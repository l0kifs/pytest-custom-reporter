"""
pytest-custom-reporter: Custom test reporter for pytest with xdist support
"""

import json
import multiprocessing
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from loguru import logger

from pytest_custom_reporter.models import TestResult, TestResultModel
from pytest_custom_reporter.settings import get_settings


class CustomReport:
    """Custom report structure for test results"""

    def __init__(self, config):
        self.config = config
        self.settings = get_settings()
        self.start_time = int(time.time() * 1000)
        self.tests: list[TestResultModel] = []
        self.summary = {
            "tests": 0,
            "passed": 0,
            "failed": 0,
            "pending": 0,
            "skipped": 0,
            "error": 0,
            "other": 0,
            "start": self.start_time,
            "stop": 0
        }
        self.verbose = config.getoption("--custom-verbose", default=False)

    def _extract_error_message(self, report, excinfo) -> str:
        """Extract error message from exception or report"""
        if excinfo and hasattr(excinfo, "value") and excinfo.value:
            if excinfo.typename == "AssertionError" and hasattr(excinfo.value, "args") and excinfo.value.args:
                return str(excinfo.value.args[0])[:500]
            return str(excinfo.value)[:500]

        if hasattr(report, "longrepr") and report.longrepr:
            lines = str(report.longrepr).split("\n")
            # Look for error line (starts with E)
            for line in lines:
                if line.strip().startswith(("E ", "E\t")):
                    return line.strip()[2:].strip()[:500]
            # Fallback to first meaningful line
            for line in lines:
                if line.strip() and not line.strip().startswith((">", "def ", "class ")):
                    return line.strip()[:500]
            return lines[0][:500] if lines else "Unknown error"

        return "Unknown error"

    def _extract_skip_reason(self, report) -> str:
        """Extract skip reason from report"""
        if hasattr(report, "longrepr") and report.longrepr:
            skip_reason = str(report.longrepr)
            if "Skipped:" in skip_reason:
                return skip_reason.split("Skipped:")[-1].strip()[:200]
            if skip_reason.startswith("(") and "Skipped:" in skip_reason:
                parts = skip_reason.split("'Skipped:")
                if len(parts) > 1:
                    return parts[-1].rstrip(")'").strip()[:200]
            return skip_reason[:200]

        if hasattr(report, "wasxfail"):
            return "Expected failure"

        return "Test was skipped"

    def _truncate_traceback(self, longrepr_str: str) -> str:
        """Truncate traceback to first and last 10 lines if too long"""
        lines = longrepr_str.split("\n")
        if len(lines) > 20:
            return "\n".join([*lines[:10], "...", *lines[-10:]])
        return "\n".join(lines)

    def _update_summary(self, result: TestResult):
        """Update summary counts for given result"""
        self.summary["tests"] += 1
        if result.value in ("passed", "failed", "skipped", "error"):
            self.summary[result.value] += 1
        else:
            self.summary["other"] += 1

    def add_test(self, item, report, result: TestResult, call=None):
        """Add test result to report"""
        try:
            # Duration is only available during call phase
            # Try to get duration from report first, then from call object
            duration = 0.0
            if report.when == "call":
                duration_value = None
                if hasattr(report, "duration"):
                    duration_value = getattr(report, "duration", None)
                # Fallback to call.duration if report.duration is not available
                if duration_value is None and call is not None and hasattr(call, "duration"):
                    duration_value = getattr(call, "duration", None)

                if duration_value is not None:
                    duration = float(duration_value)

            # Extract marks from item
            marks = [mark.name for mark in item.iter_markers()] if hasattr(item, "iter_markers") else []

            # Extract allure.id if present (stored in allure_label marker)
            allure_id = None
            try:
                if hasattr(item, "iter_markers"):
                    # Allure stores ID in allure_label mark with label_type="as_id"
                    for mark in item.iter_markers("allure_label"):
                        if mark.kwargs.get("label_type") == "as_id" and mark.args:
                            allure_id = str(mark.args[0])
                            break
            except Exception as e:
                logger.debug(
                    f"Failed to extract allure_id: {e}",
                    extra={"component": "CustomReport", "test_nodeid": item.nodeid}
                )

            # Create test result model
            test_result = TestResultModel(
                nodeid=item.nodeid,
                name=item.name if hasattr(item, "name") else item.nodeid,
                duration=duration,
                start_time=datetime.fromtimestamp(self.start_time / 1000),
                result=result,
                marks=marks,
                allure_id=allure_id,
            )

            # For failures and errors, include detailed information
            if result in (TestResult.FAILED, TestResult.ERROR):
                excinfo = getattr(report, "excinfo", None) if hasattr(report, "excinfo") else None
                test_result.message = self._extract_error_message(report, excinfo)

                if hasattr(report, "longrepr") and report.longrepr:
                    test_result.stack_trace = self._truncate_traceback(str(report.longrepr))

                log_level = logger.warning if result == TestResult.FAILED else logger.error
                log_level(
                    f"Test {result.value}",
                    extra={
                        "component": "CustomReport",
                        "test_nodeid": item.nodeid,
                        "exception_type": excinfo.typename if excinfo and hasattr(excinfo, "typename") else None
                    }
                )

            # For skipped tests, include reason
            elif result == TestResult.SKIPPED:
                test_result.message = self._extract_skip_reason(report)

            self.tests.append(test_result)
            self._update_summary(result)
        except Exception as e:
            # Log error but don't fail - continue processing other tests
            logger.error(
                "Failed to add test to report",
                extra={
                    "component": "CustomReport",
                    "test_nodeid": getattr(item, "nodeid", "unknown"),
                    "result": result.value if isinstance(result, TestResult) else str(result),
                    "error": str(e)
                },
                exc_info=True
            )

    def _get_xdist_worker_count(self) -> int | None:
        """Get xdist worker count if available"""
        try:
            if hasattr(self.config.option, "numprocesses") and self.config.option.numprocesses:
                return self.config.option.numprocesses
            if hasattr(self.config.option, "n") and self.config.option.n:
                n_value = self.config.option.n
                if isinstance(n_value, str) and n_value.lower() == "auto":
                    return multiprocessing.cpu_count()
                if isinstance(n_value, int):
                    return n_value
        except Exception as e:  # Log but don't fail if worker count detection fails
            logger.debug(
                "Failed to detect xdist worker count",
                extra={
                    "component": "CustomReport",
                    "error": str(e)
                }
            )
        return None

    def finalize(self) -> dict[str, Any]:
        """Generate final CTRF report structure"""
        try:
            self.summary["stop"] = int(time.time() * 1000)
            duration_ms = self.summary["stop"] - self.summary["start"]

            environment = {
                "pythonVersion": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "pytestVersion": pytest.__version__,
            }

            worker_count = self._get_xdist_worker_count()
            if worker_count is not None:
                environment["xdistWorkers"] = worker_count

            # Convert test models to CTRF format
            tests_ctrf = []
            for test in self.tests:
                test_dict = {
                    "name": test.nodeid,
                    "status": test.result.value,
                    "duration": int(test.duration * 1000),  # Convert to milliseconds
                }
                
                # Add optional fields if present
                if test.message:
                    test_dict["message"] = test.message
                if test.stack_trace:
                    test_dict["trace"] = test.stack_trace
                if test.marks:
                    test_dict["marks"] = test.marks
                if test.allure_id:
                    test_dict["allure_id"] = test.allure_id
                
                tests_ctrf.append(test_dict)

            report = {
                "results": {
                    "tool": {
                        "name": "pytest",
                        "version": pytest.__version__
                    },
                    "summary": self.summary,
                    "tests": tests_ctrf,
                    "environment": environment,
                    "extra": {
                        "aiOptimized": True,
                        "ctrf": "1.0.0",
                        "tokenEfficient": not self.verbose,
                        "generatedAt": int(time.time() * 1000),
                        "pluginName": self.settings.name,
                        "pluginVersion": self.settings.version
                    }
                }
            }

            logger.info(
                "Custom report finalized",
                extra={
                    "component": "CustomReport",
                    "total_tests": self.summary["tests"],
                    "passed": self.summary["passed"],
                    "failed": self.summary["failed"],
                    "skipped": self.summary["skipped"],
                    "duration_ms": duration_ms
                }
            )

            return report
        except Exception as e:
            # Return partial report if finalization fails
            logger.error(
                "Failed to finalize report, returning partial report",
                extra={
                    "component": "CustomReport",
                    "error": str(e)
                },
                exc_info=True
            )
            # Return minimal valid report structure
            return {
                "results": {
                    "tool": {
                        "name": "pytest",
                        "version": pytest.__version__ if hasattr(pytest, "__version__") else "unknown"
                    },
                    "summary": self.summary,
                    "tests": self.tests,
                    "environment": {},
                    "extra": {
                        "aiOptimized": True,
                        "ctrf": "1.0.0",
                        "tokenEfficient": not self.verbose,
                        "generatedAt": int(time.time() * 1000),
                        "error": "Report finalization failed",
                        "error_message": str(e)
                    }
                }
            }


class CustomReporterPlugin:
    """Pytest plugin for custom reporting"""

    def __init__(self, config):
        self.config = config
        self.settings = get_settings()
        self.report = CustomReport(config)
        self.report_format = config.getoption("--custom-report-format", default=self.settings.report_format)
        user_specified_file = config.getoption("--custom-report-file", default=self.settings.report_file)
        self.output_file = self._generate_output_path(user_specified_file)
        self.remote_url = config.getoption("--custom-report-url", default=self.settings.report_url)
        self._processed_tests: set[str] = set()  # Track processed test nodeids
        logger.info(
            "Custom Reporter plugin initialized",
            extra={
                "component": "CustomReporterPlugin",
                "plugin_name": self.settings.name,
                "plugin_version": self.settings.version,
                "output_file": self.output_file,
                "format": self.report_format,
                "remote_url": self.remote_url
            }
        )

    def _generate_output_path(self, user_specified_file: str | None) -> str:
        """Generate unique output file path in custom_reports directory"""
        # Default directory for reports
        reports_dir = Path("custom_reports")
        # Get default extension based on format
        default_extension = f".{self.report_format}"

        if user_specified_file:
            # If user specified a file, check if it's a full path or just filename
            user_path = Path(user_specified_file)
            if user_path.is_absolute() or user_path.parent != Path():
                # User specified a full path or path with directory
                # If no extension, add format extension
                if not user_path.suffix:
                    return str(user_path.with_suffix(default_extension))
                return str(user_path)
            else:
                # User specified just a filename, put it in ai_reports with unique name
                base_name = user_path.stem
                extension = user_path.suffix or default_extension
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                unique_filename = f"{base_name}-{timestamp}{extension}"
                return str(reports_dir / unique_filename)
        else:
            # Default: generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            return str(reports_dir / f"report-{timestamp}{default_extension}")

    def _send_to_remote_server(self, report_data: dict[str, Any]) -> bool:
        """Send report to remote server via REST API"""
        if not self.remote_url:
            return False

        try:
            logger.info(
                "Sending report to remote server",
                extra={
                    "component": "CustomReporterPlugin",
                    "url": self.remote_url,
                    "test_count": report_data["results"]["summary"]["tests"]
                }
            )

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.remote_url,
                    json=report_data,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "pytest-custom-reporter/1.0.0"
                    }
                )
                response.raise_for_status()

            logger.info(
                "Report successfully sent to remote server",
                extra={
                    "component": "CustomReporterPlugin",
                    "url": self.remote_url,
                    "status_code": response.status_code
                }
            )
            return True

        except httpx.TimeoutException as e:
            logger.error(
                "Timeout while sending report to remote server",
                extra={
                    "component": "CustomReporterPlugin",
                    "url": self.remote_url,
                    "error": str(e)
                }
            )
            return False
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error while sending report to remote server",
                extra={
                    "component": "CustomReporterPlugin",
                    "url": self.remote_url,
                    "status_code": e.response.status_code,
                    "error": str(e)
                }
            )
            return False
        except Exception as e:
            logger.error(
                "Failed to send report to remote server",
                extra={
                    "component": "CustomReporterPlugin",
                    "url": self.remote_url,
                    "error": str(e)
                },
                exc_info=True
            )
            return False

    def _map_outcome_to_result(self, report) -> TestResult:
        """Map pytest outcome to TestResult enum"""
        outcome = report.outcome
        
        # Setup failures should be mapped to error
        if report.when == "setup" and outcome == "failed":
            return TestResult.ERROR
        
        # Map standard outcomes
        if outcome == "passed":
            return TestResult.PASSED
        elif outcome == "failed":
            return TestResult.FAILED
        elif outcome == "skipped":
            return TestResult.SKIPPED
        elif outcome == "error":
            return TestResult.ERROR
        else:
            return TestResult.OTHER

    def _is_worker(self, session) -> bool:
        """Check if running on xdist worker"""
        try:
            import xdist  # noqa: PLC0415
            return xdist.get_xdist_worker_id(session) != "master"
        except (ImportError, AttributeError):
            return hasattr(self.config, "workerinput")

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        """Hook to capture test results"""
        outcome = yield
        report = outcome.get_result()

        try:
            # Process during call phase for normal tests, or setup phase for skipped/failed tests
            # Also capture setup failures (e.g., database connection errors)
            should_process = (
                report.when == "call"
                or (report.when == "setup" and report.outcome in ("skipped", "failed", "error"))
            )
            is_new_test = report.when == "call" or item.nodeid not in self._processed_tests

            if should_process and is_new_test:
                self._processed_tests.add(item.nodeid)
                # Map pytest outcomes to TestResult enum
                # Setup/teardown failures should be mapped to "error" status
                # Test execution failures remain as "failed"
                result = self._map_outcome_to_result(report)
                # Pass call object to get duration if report.duration is not available
                self.report.add_test(item, report, result, call)
        except Exception as e:
            # Log error but don't raise - plugin failures should not break test execution
            logger.error(
                "Error in pytest_runtest_makereport hook",
                extra={
                    "component": "CustomReporterPlugin",
                    "test_nodeid": getattr(item, "nodeid", "unknown"),
                    "error": str(e)
                },
                exc_info=True
            )

    def pytest_testnodedown(self, node, error):
        """Called when a worker node finishes - collect results from worker"""
        try:
            if hasattr(node, "workeroutput") and "custom_reporter_results" in node.workeroutput:
                worker_results = node.workeroutput["custom_reporter_results"]
                if isinstance(worker_results, dict) and "tests" in worker_results:
                    # Deserialize worker test results into TestResultModel instances
                    for test_dict in worker_results["tests"]:
                        test_model = TestResultModel(**test_dict)
                        self.report.tests.append(test_model)
                        # Update summary counts using shared method
                        self.report._update_summary(test_model.result)
        except (AttributeError, KeyError) as e:
            logger.warning(
                "Error collecting worker results",
                extra={
                    "component": "CustomReporterPlugin",
                    "worker_id": getattr(node, "workerid", "unknown"),
                    "error": str(e)
                }
            )

    def pytest_sessionfinish(self, session):
        """Generate and save report at end of session"""
        try:
            # Check if we're on a worker - if so, send results to master
            if self._is_worker(session):
                try:
                    if hasattr(session.config, "workeroutput"):
                        # Serialize test models to dicts for worker communication
                        # Use mode='json' to ensure datetime objects are converted to strings
                        tests_dicts = [test.model_dump(mode='json') for test in self.report.tests]
                        session.config.workeroutput["custom_reporter_results"] = {
                            "tests": tests_dicts,
                            "start": self.report.start_time
                        }
                except Exception as e:
                    logger.error(
                        "Failed to send worker results to master",
                        extra={
                            "component": "CustomReporterPlugin",
                            "error": str(e)
                        },
                        exc_info=True
                    )
                return

            # We're on master - finalize and save report
            final_report = self.report.finalize()
            output_path = Path(self.output_file)

            # Create output directory - log error but don't raise
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(
                    "Failed to create output directory",
                    extra={
                        "component": "CustomReporterPlugin",
                        "output_path": str(output_path),
                        "error": str(e)
                    },
                    exc_info=True
                )
                # Don't raise - test execution already completed successfully
                return

            # Write report file - log error but don't raise
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    if self.report_format == "yaml":
                        yaml.dump(final_report, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                    else:
                        json.dump(final_report, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(
                    "Failed to write report file",
                    extra={
                        "component": "CustomReporterPlugin",
                        "output_path": str(output_path),
                        "format": self.report_format,
                        "error": str(e)
                    },
                    exc_info=True
                )
                # Don't raise - test execution already completed successfully
                return

            # Send report to remote server if URL is configured
            if self.remote_url:
                self._send_to_remote_server(final_report)

            # Print summary - wrap in try-except to prevent print errors from breaking execution
            try:
                summary = final_report["results"]["summary"]
                print(f"\n{'='*60}")
                print(f"Custom Report Generated: {output_path}")
                print(f"{'='*60}")
                print(f"Total Tests: {summary['tests']}")
                print(f"? Passed: {summary['passed']}")
                print(f"? Failed: {summary['failed']}")
                if summary.get("error", 0) > 0:
                    print(f"? Error: {summary['error']}")
                print(f"? Skipped: {summary['skipped']}")
                print(f"Duration: {(summary['stop'] - summary['start']) / 1000:.2f}s")
                print(f"{'='*60}\n")
            except Exception as e:
                logger.warning(
                    "Failed to print report summary",
                    extra={
                        "component": "CustomReporterPlugin",
                        "error": str(e)
                    }
                )
        except Exception as e:
            # Catch-all for any unexpected errors - log but don't raise
            logger.error(
                "Unexpected error in pytest_sessionfinish",
                extra={
                    "component": "CustomReporterPlugin",
                    "error": str(e)
                },
                exc_info=True
            )
            # Don't raise - test execution already completed successfully


def pytest_addoption(parser):
    """Add command line options"""
    settings = get_settings()
    group = parser.getgroup("custom-reporter")
    group.addoption(
        "--custom-report",
        action="store_true",
        default=settings.generate_report,
        help="Generate custom report"
    )
    group.addoption(
        "--custom-report-file",
        action="store",
        default=settings.report_file,
        help="Output file for custom report (default: custom_reports/report-YYYYMMDD-HHMMSS.json). "
             "If only filename is provided, it will be placed in custom_reports/ with timestamp. "
             "Full paths are preserved as-is."
    )
    group.addoption(
        "--custom-report-url",
        action="store",
        default=settings.report_url,
        help="Remote server URL to send the report to via HTTP POST. "
             "Report will be sent as JSON in the request body."
    )
    group.addoption(
        "--custom-report-format",
        action="store",
        default=settings.report_format,
        help="Report format: json or yaml (default: json)"
    )


def pytest_configure(config):
    """Register plugin if --custom-report is enabled"""
    if config.getoption("--custom-report"):
        try:
            # Check if plugin instance is already registered to avoid double registration
            # The entry point loads the module, but we need to register the instance
            plugin_name = "custom_reporter_instance"
            if not config.pluginmanager.hasplugin(plugin_name):
                logger.info(
                    "Registering Custom Reporter plugin",
                    extra={
                        "component": "pytest_configure",
                    }
                )
                config.pluginmanager.register(CustomReporterPlugin(config), plugin_name)
        except Exception as e:
            # Log error but don't raise - allow pytest to start without plugin
            logger.error(
                "Failed to initialize Custom Reporter plugin",
                extra={
                    "component": "pytest_configure",
                    "error": str(e)
                },
                exc_info=True
            )
            # Don't raise - allow tests to run without the reporting plugin
