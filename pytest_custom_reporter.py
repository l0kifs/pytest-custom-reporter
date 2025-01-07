"""
To use this custom reporter, you need to add the following lines to your conftest.py file:

```python
    import pytest_custom_reporter  # import the reporter module
    
    def pytest_configure(config):
        config.pluginmanager.register(pytest_custom_reporter, name="pytest_custom_reporter")
```

"""

from datetime import datetime, timezone
import logging
import os
import queue
import sys
import threading

import pytest
from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


ADDON_DATA_DIR = 'custom_reports'

log = logging.getLogger(__name__)

Base = declarative_base()

class TestResult(Base):
    __tablename__ = "test_results"
    id = Column(Integer, primary_key=True)
    test_name = Column(String, nullable=False)
    outcome = Column(String, nullable=False)
    duration = Column(Float, nullable=False)
    exception = Column(String, nullable=True)
    short_exception = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    
    
class DBHandler:
    def __init__(self, db_file_path=f"{ADDON_DATA_DIR}/custom_reports.db"):
        self.db_file_path = db_file_path
        self.engine = create_engine(f'sqlite:///{db_file_path}', echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.queue = queue.Queue()
        self.stop_event = threading.Event()

        # Start the worker thread
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def _worker(self):
        session = self.Session()
        while not self.stop_event.is_set() or not self.queue.empty():
            try:
                test_result = self.queue.get(timeout=1)
                session.add(TestResult(**test_result))
                session.commit()
            except queue.Empty:
                pass
            except Exception as e:
                session.rollback()
                log.error(f"Error saving test result: {e}")
        session.close()

    def add_result(self, result):
        self.queue.put(result)

    def close(self):
        self.stop_event.set()
        self.worker_thread.join()
        
    def remove_db_file(self):
        os.remove(self.db_file_path)
        
        
def pytest_configure(config: pytest.Config):
    if "--collect-only" in sys.argv:
        log.info("Skipping custom reporter for --collect-only")
        config.pluginmanager.unregister(name="pytest_custom_reporter")
        

def pytest_sessionstart(
    session: pytest.Session
):
    if not hasattr(session.config, "workerinput"):
        os.makedirs(ADDON_DATA_DIR, exist_ok=True)
    
    session.db_handler = DBHandler()


def pytest_sessionfinish(
    session: pytest.Session, 
    exitstatus: int
):
    if hasattr(session, "db_handler"):
        session.db_handler.close()
    
    if not hasattr(session.config, "workerinput"):
        generate_reports()
        session.db_handler.remove_db_file()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, 
    call: pytest.CallInfo
):
    outcome = yield
    report: pytest.TestReport = outcome.get_result()
    if report.when == "call":
        item.session.db_handler.add_result({
            'test_name': report.nodeid,
            'outcome': report.outcome,
            'duration': report.duration,
            'exception': str(report.longrepr)[:1000] if report.failed else None,
            'short_exception': str(report.longrepr.chain[-1][0]) if report.failed and report.longrepr.chain else None,
        })


def generate_reports():
    handler = DBHandler()
    session = handler.Session()
    results = session.query(TestResult).all()
    session.close()
    
    with open(os.path.join(ADDON_DATA_DIR, "failed_vs_passed_tests_number.txt"), "w") as file:
        failed_tests = [result for result in results if result.outcome == "failed"]
        passed_tests = [result for result in results if result.outcome == "passed"]
        file.write(f"Failed tests: {len(failed_tests)}\n")
        file.write(f"Passed tests: {len(passed_tests)}\n")
