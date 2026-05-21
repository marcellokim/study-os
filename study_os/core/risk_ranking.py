from __future__ import annotations

from study_os.core.models import QueueEntry


_FALLBACK_ORDER = 10**9
_PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
_RESULT_ORDER = {"wrong": 0, "partial": 1, "uncertain": 2, "correct": 3}
_CORRECT_CONFIDENCE_ORDER = {"low": 0, "unknown": 1, "medium": 2, "high": 3}
_INCORRECT_CONFIDENCE_ORDER = {"high": 0, "medium": 1, "unknown": 2, "low": 3}


def _confidence_risk_order(entry: QueueEntry) -> int:
    if entry.last_result == "correct":
        return _CORRECT_CONFIDENCE_ORDER.get(entry.confidence, len(_CORRECT_CONFIDENCE_ORDER))

    return _INCORRECT_CONFIDENCE_ORDER.get(entry.confidence, len(_INCORRECT_CONFIDENCE_ORDER))


def queue_entry_exam_risk_key(entry: QueueEntry) -> tuple[int, int, int, bool, int, str, str]:
    return (
        _PRIORITY_ORDER.get(entry.priority, len(_PRIORITY_ORDER)),
        _RESULT_ORDER.get(entry.last_result, len(_RESULT_ORDER)),
        _confidence_risk_order(entry),
        entry.next_review_day is None,
        entry.next_review_day if entry.next_review_day is not None else _FALLBACK_ORDER,
        entry.next_review_date or "",
        entry.item_id,
    )
