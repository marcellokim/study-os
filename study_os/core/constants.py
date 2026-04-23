from __future__ import annotations

from enum import Enum


class StudyStatus(str, Enum):
    NEW = "NEW"
    LEARNED = "LEARNED"
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    FINAL = "FINAL"
    MASTERED = "MASTERED"


class Result(str, Enum):
    CORRECT = "correct"
    WRONG = "wrong"
    PARTIAL = "partial"
    UNCERTAIN = "uncertain"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ErrorCode(str, Enum):
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"
    C6 = "C6"
    C7 = "C7"
    C8 = "C8"


RISK_ERROR_CODES = frozenset(
    {
        ErrorCode.C2.value,
        ErrorCode.C3.value,
        ErrorCode.C6.value,
        ErrorCode.C8.value,
    }
)
STATUS_ORDER = tuple(status.value for status in StudyStatus)
