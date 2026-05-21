from __future__ import annotations

from typing import Any

from study_os.core.models import Item
from study_os.core.packet_progress import build_progress_key, confidence_score_to_level


_BLOCKER_ERROR_CODE = {
    "concept": "C1",
    "memory": "C1",
    "prerequisite": "C1",
    "prerequisite_gap": "C1",
    "source_confusion": "C1",
    "concept_connection_gap": "C2",
    "application": "C4",
    "code": "C4",
    "code_gap": "C4",
    "math": "C5",
    "math_gap": "C5",
    "visual": "C6",
    "visualization_gap": "C6",
    "wording": "C7",
    "terminology": "C7",
    "terminology_gap": "C7",
}
_RESULTS = frozenset({"correct", "partial", "wrong", "uncertain"})


def _phase_for_packet(packet_type: str) -> str:
    return "learning" if packet_type == "learning" else "review"


def _confidence_for(progress: dict[str, Any]) -> str:
    confidence_score = progress.get("confidence_score")
    if isinstance(confidence_score, int) and not isinstance(confidence_score, bool):
        return confidence_score_to_level(confidence_score)

    confidence = progress.get("confidence")
    if isinstance(confidence, str):
        return confidence
    return "unknown"


def _note_for(progress: dict[str, Any]) -> str:
    parts: list[str] = []
    blocker_type = progress.get("blocker_type")
    draft_answer = progress.get("draft_answer")
    if isinstance(blocker_type, str) and blocker_type:
        parts.append(f"blocker={blocker_type}")
    if isinstance(draft_answer, str) and draft_answer:
        parts.append(f"answer={draft_answer}")
    return "; ".join(parts)


def _is_next_focus(result: str, confidence: str) -> bool:
    return result in {"wrong", "partial", "uncertain"} or (result == "correct" and confidence == "low")


def build_close_session_draft(
    *,
    course_slug: str,
    session_date: str,
    packet_type: str,
    day_index: int | None,
    packet_progress: dict[str, Any],
    items_by_id: dict[str, Item],
) -> dict[str, Any]:
    progress_key = build_progress_key(packet_type=packet_type, day_index=day_index)
    packet_items = packet_progress.get(progress_key, {})
    if not isinstance(packet_items, dict):
        packet_items = {}

    reviewed_items: list[dict[str, Any]] = []
    next_focus: list[str] = []

    for item_id in sorted(packet_items):
        if item_id not in items_by_id:
            continue

        progress = packet_items[item_id]
        if not isinstance(progress, dict):
            continue

        result = progress.get("result")
        if result not in _RESULTS:
            continue

        confidence = _confidence_for(progress)
        reviewed: dict[str, Any] = {
            "item_id": item_id,
            "phase": _phase_for_packet(packet_type),
            "result": result,
            "confidence": confidence,
        }

        blocker_type = progress.get("blocker_type")
        error_code = _BLOCKER_ERROR_CODE.get(blocker_type) if isinstance(blocker_type, str) else None
        if result != "correct" and error_code is not None:
            reviewed["error_code"] = error_code

        note = _note_for(progress)
        if note:
            reviewed["note"] = note

        reviewed_items.append(reviewed)
        if _is_next_focus(result, confidence):
            next_focus.append(item_id)

    draft: dict[str, Any] = {
        "course_slug": course_slug,
        "session_date": session_date,
        "reviewed_items": reviewed_items,
        "next_focus": next_focus,
    }
    if day_index is not None:
        draft["day_index"] = day_index
    return draft
