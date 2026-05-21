from __future__ import annotations

from study_os.core.models import QueueEntry


_FALLBACK_ORDER = 10**9
_PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
_RESULT_ORDER = {"wrong": 0, "partial": 1, "uncertain": 2, "correct": 3}
_CONFIDENCE_ORDER = {"low": 0, "unknown": 1, "medium": 2, "high": 3}


def queue_entry_exam_risk_key(entry: QueueEntry) -> tuple[int, int, int, bool, int, str, str]:
    return (
        _PRIORITY_ORDER.get(entry.priority, len(_PRIORITY_ORDER)),
        _RESULT_ORDER.get(entry.last_result, len(_RESULT_ORDER)),
        _CONFIDENCE_ORDER.get(entry.confidence, len(_CONFIDENCE_ORDER)),
        entry.next_review_day is None,
        entry.next_review_day if entry.next_review_day is not None else _FALLBACK_ORDER,
        entry.next_review_date or "",
        entry.item_id,
    )
