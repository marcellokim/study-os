from __future__ import annotations

from datetime import date, timedelta

from study_os.core.constants import Confidence, Priority, RISK_ERROR_CODES, Result, StudyStatus
from study_os.core.models import Block, Item, MasteryRecord, QueueEntry


REPAIR_RESULTS = {Result.WRONG.value, Result.PARTIAL.value, Result.UNCERTAIN.value}

BASE_GAPS = {
    StudyStatus.R0.value: 0,
    StudyStatus.R1.value: 2,
    StudyStatus.R2.value: 5,
}


def build_queue_entry(
    record: MasteryRecord,
    item: Item,
    block: Block,
    exam_date: str,
    today: str,
    *,
    current_day: int,
    recent_error_codes: list[str],
    unresolved_visual: bool,
) -> QueueEntry | None:
    if record.status in {StudyStatus.NEW.value, StudyStatus.LEARNED.value, StudyStatus.MASTERED.value}:
        return None

    exam_day = date.fromisoformat(exam_date)
    today_day = date.fromisoformat(today)
    days_to_exam = max((exam_day - today_day).days, 0)

    reasons: list[str] = []
    risk_score = 0

    if block.importance == "high":
        risk_score += 1
        reasons.append("important block")
    if item.difficulty == "hard":
        risk_score += 1
        reasons.append("hard item")
    if record.last_result == Result.PARTIAL.value:
        risk_score += 2
        reasons.append("last result partial")
    if record.last_result == Result.UNCERTAIN.value:
        risk_score += 2
        reasons.append("last result uncertain")
    if record.last_result == Result.WRONG.value:
        risk_score += 1
        reasons.append("last result wrong")
    if record.last_result == Result.WRONG.value and record.last_confidence == Confidence.HIGH.value:
        risk_score += 2
        reasons.append("overconfidence")
    if record.last_result == Result.CORRECT.value and record.last_confidence == Confidence.LOW.value:
        risk_score += 2
        reasons.append("low confidence correct")
    if any(code in RISK_ERROR_CODES for code in recent_error_codes):
        risk_score += 2
        reasons.append("risk error code")
    if unresolved_visual:
        risk_score += 2
        reasons.append("visual pending")
    if days_to_exam <= 2:
        risk_score += 2
        reasons.append("exam near")

    needs_same_day_repair = (
        record.last_result in REPAIR_RESULTS
        or (record.last_result == Result.CORRECT.value and record.last_confidence == Confidence.LOW.value)
    )

    if record.status == StudyStatus.FINAL.value:
        default_gap = max((max(today_day, exam_day - timedelta(days=1)) - today_day).days, 0)
        if needs_same_day_repair or risk_score >= 4:
            gap = 0
        elif risk_score >= 2:
            gap = min(default_gap, 1)
        else:
            gap = default_gap
        next_review_date = today_day + timedelta(days=gap)
        next_review_day = current_day + gap
    else:
        base_gap = BASE_GAPS[record.status]
        gap = 0 if needs_same_day_repair else max(0, base_gap - min(risk_score, base_gap))
        next_review_date = today_day + timedelta(days=gap)
        next_review_day = current_day + gap

    if record.status == StudyStatus.R0.value or risk_score >= 4:
        priority = Priority.URGENT.value
    elif risk_score >= 2:
        priority = Priority.HIGH.value
    elif risk_score == 1:
        priority = Priority.MEDIUM.value
    else:
        priority = Priority.LOW.value

    return QueueEntry(
        item_id=record.item_id,
        block_id=record.block_id,
        status=record.status,
        priority=priority,
        last_result=record.last_result,
        confidence=record.last_confidence,
        next_review_day=next_review_day,
        next_review_date=next_review_date.isoformat(),
        reason=", ".join(reasons) if reasons else "scheduled by state policy",
    )
