from enum import Enum
from datetime import datetime

from pydantic import BaseModel


class TestResult(Enum):
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    SKIPPED = "skipped"
    ERROR = "error"
    OTHER = "other"


class TestResultModel(BaseModel):
    nodeid: str
    name: str
    duration: float = 0.0
    start_time: datetime | None = None
    result: TestResult = TestResult.OTHER
    environment: str | None = None
    marks: list[str] = []
    params: dict[str, str] = {}
    stack_trace: str | None = None
    message: str | None = None
    allure_id: str | None = None
