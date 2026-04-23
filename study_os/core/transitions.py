from __future__ import annotations

from dataclasses import replace

from study_os.core.constants import Confidence, RISK_ERROR_CODES, Result, StudyStatus
from study_os.core.models import MasteryRecord, ReviewedItemUpdate


PROMOTION_ORDER = [
    StudyStatus.R0.value,
    StudyStatus.R1.value,
    StudyStatus.R2.value,
    StudyStatus.FINAL.value,
    StudyStatus.MASTERED.value,
]
REGRESSION_INDEX = {
    StudyStatus.NEW.value: 0,
    StudyStatus.LEARNED.value: 0,
    StudyStatus.R0.value: 0,
    StudyStatus.R1.value: 1,
    StudyStatus.R2.value: 2,
    StudyStatus.FINAL.value: 3,
    StudyStatus.MASTERED.value: 4,
}


def _promote(status: str) -> str:
    if status in {StudyStatus.NEW.value, StudyStatus.LEARNED.value}:
        return StudyStatus.R0.value
    index = PROMOTION_ORDER.index(status)
    return PROMOTION_ORDER[min(index + 1, len(PROMOTION_ORDER) - 1)]


def _regress(status: str, strong: bool) -> str:
    if status in {StudyStatus.NEW.value, StudyStatus.LEARNED.value, StudyStatus.R0.value}:
        return StudyStatus.R0.value if status == StudyStatus.R0.value else StudyStatus.NEW.value
    index = REGRESSION_INDEX[status]
    shift = 2 if strong else 1
    new_index = max(0, index - shift)
    return PROMOTION_ORDER[new_index]


def apply_review_update(record: MasteryRecord, update: ReviewedItemUpdate, review_date: str) -> MasteryRecord:
    strong_regression = update.confidence == Confidence.HIGH.value or (update.error_code in RISK_ERROR_CODES)

    if update.phase == "learning":
        new_status = StudyStatus.R0.value
        return replace(
            record,
            status=new_status,
            last_result=update.result,
            last_confidence=update.confidence,
            consecutive_successes=1 if update.result == Result.CORRECT.value else 0,
            last_review_date=review_date,
            reason=update.note or "learning session recorded",
        )

    if update.result == Result.CORRECT.value:
        if update.confidence == Confidence.LOW.value:
            new_status = record.status
        else:
            new_status = _promote(record.status)
        consecutive_successes = record.consecutive_successes + 1
    elif update.result == Result.PARTIAL.value:
        new_status = record.status if record.status == StudyStatus.R0.value else _regress(record.status, strong=False)
        consecutive_successes = 0
    elif update.result == Result.UNCERTAIN.value:
        new_status = record.status
        consecutive_successes = 0
    else:
        new_status = _regress(record.status, strong=strong_regression)
        consecutive_successes = 0

    return replace(
        record,
        status=new_status,
        last_result=update.result,
        last_confidence=update.confidence,
        consecutive_successes=consecutive_successes,
        last_review_date=review_date,
        reason=update.note or record.reason,
    )
