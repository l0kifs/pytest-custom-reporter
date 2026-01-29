"""Verification tests for allure_id collection in reports"""
import json
from pathlib import Path

import pytest


@pytest.fixture
def reports_dir():
    """Fixture to get the custom_reports directory"""
    return Path("custom_reports")


@pytest.fixture
def latest_allure_report(reports_dir):
    """Fixture to get the report from test_allure_integration run"""
    # Find the most recent report file
    report_files = sorted(reports_dir.glob("report-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    # Look for a report that contains allure integration tests
    for report_file in report_files:
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Check if this report contains our allure integration tests
            tests = data["results"]["tests"]
            if any("test_allure_integration" in test["name"] for test in tests):
                return data
    
    pytest.skip("No allure integration report found. Run test_allure_integration.py first.")


def find_test_by_name(report_data, test_name):
    """Helper to find a test by name in the report"""
    for test in report_data["results"]["tests"]:
        if test_name in test["name"]:
            return test
    return None


def test_report_contains_allure_ids(latest_allure_report):
    """Verify that the report contains allure_id fields"""
    tests = latest_allure_report["results"]["tests"]
    
    # Find tests with allure_id
    tests_with_id = [test for test in tests if test.get("allure_id")]
    
    # Should have at least one test with allure_id
    assert len(tests_with_id) > 0, f"No tests with allure_id found in report. Total tests: {len(tests)}"
    
    print(f"\nFound {len(tests_with_id)} tests with allure_id out of {len(tests)} total tests")


def test_specific_allure_ids(latest_allure_report):
    """Verify specific allure_id values are captured correctly"""
    # Check TEST-001
    test_001 = find_test_by_name(latest_allure_report, "test_with_allure_id")
    assert test_001 is not None, "test_with_allure_id not found in report"
    assert test_001.get("allure_id") == "TEST-001", \
        f"Expected TEST-001, got {test_001.get('allure_id')}"
    
    # Check TEST-002
    test_002 = find_test_by_name(latest_allure_report, "test_another_with_allure_id")
    assert test_002 is not None, "test_another_with_allure_id not found in report"
    assert test_002.get("allure_id") == "TEST-002", \
        f"Expected TEST-002, got {test_002.get('allure_id')}"
    
    # Check TEST-003 (skipped test)
    test_003 = find_test_by_name(latest_allure_report, "test_skipped_with_allure_id")
    assert test_003 is not None, "test_skipped_with_allure_id not found in report"
    assert test_003.get("allure_id") == "TEST-003", \
        f"Expected TEST-003, got {test_003.get('allure_id')}"


def test_without_allure_id_has_none(latest_allure_report):
    """Verify test without allure_id doesn't have the field or has None"""
    test_no_id = find_test_by_name(latest_allure_report, "test_without_allure_id")
    
    if test_no_id:
        allure_id = test_no_id.get("allure_id")
        assert allure_id is None or "allure_id" not in test_no_id, \
            f"Test without allure_id should have None or no field, got: {allure_id}"


def test_parametrized_tests_have_allure_id(latest_allure_report):
    """Verify parametrized tests preserve allure_id"""
    tests = latest_allure_report["results"]["tests"]
    
    # Find parametrized tests with allure_id
    parametrized_tests = [test for test in tests if "test_parametrized_with_allure_id" in test["name"]]
    
    assert len(parametrized_tests) == 3, \
        f"Expected 3 parametrized test instances, found {len(parametrized_tests)}"
    
    # All parametrized tests should have the same allure_id
    for test in parametrized_tests:
        assert test.get("allure_id") == "TEST-005", \
            f"Parametrized test {test['name']} should have allure_id TEST-005, got {test.get('allure_id')}"


def test_class_test_has_allure_id(latest_allure_report):
    """Verify tests in classes preserve allure_id"""
    test_in_class = find_test_by_name(latest_allure_report, "test_in_class_with_allure_id")
    
    assert test_in_class is not None, "test_in_class_with_allure_id not found in report"
    assert test_in_class.get("allure_id") == "TEST-100", \
        f"Class test should have allure_id TEST-100, got {test_in_class.get('allure_id')}"


def test_class_test_without_allure_id(latest_allure_report):
    """Verify tests in classes without allure_id marker don't have allure_id"""
    test_in_class = find_test_by_name(latest_allure_report, "test_in_class_without_allure_id")
    
    if test_in_class:
        allure_id = test_in_class.get("allure_id")
        assert allure_id is None or "allure_id" not in test_in_class, \
            f"Test without allure_id should have None or no field, got: {allure_id}"


def test_allure_label_mark_present(latest_allure_report):
    """Verify that allure_label marker appears in the marks list"""
    test_with_id = find_test_by_name(latest_allure_report, "test_with_allure_id")
    
    assert test_with_id is not None, "test_with_allure_id not found in report"
    marks = test_with_id.get("marks", [])
    # Allure adds allure_label mark when using @allure.id()
    assert "allure_label" in marks, \
        f"allure_label should be in marks list when using @allure.id(), got: {marks}"
