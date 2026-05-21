from __future__ import annotations

import re
import sys
from copy import deepcopy
from typing import Any, Union

from study_os.core.constants import Confidence, Result

if sys.version_info >= (3, 10):
    PacketProgressItem = dict[str, bool | int | str]
else:
    PacketProgressItem = dict[str, Union[bool, int, str]]
PacketProgressPayload = dict[str, dict[str, PacketProgressItem]]
_DAY_KEY_PATTERN = re.compile(r"^(?P<packet_type>[^:]+):day:(?P<day_index>[1-9][0-9]*)$")
_NON_DAY_PACKET_TYPES = frozenset({"final_recall"})
_RESULT_VALUES = {result.value for result in Result}
_CONFIDENCE_VALUES = {confidence.value for confidence in Confidence}
_M0_BLOCKER_TYPE_VALUES = frozenset(
    {
        "concept",
        "memory",
        "application",
        "visual",
        "wording",
        "careless",
        "unknown",
    }
)
_LEGACY_BLOCKER_TYPE_VALUES = frozenset(
    {
        "prerequisite_gap",
        "concept_connection_gap",
        "math_gap",
        "code_gap",
        "visualization_gap",
        "terminology_gap",
        "source_confusion",
    }
)
_BLOCKER_TYPE_VALUES = _M0_BLOCKER_TYPE_VALUES | _LEGACY_BLOCKER_TYPE_VALUES


def empty_packet_progress() -> PacketProgressPayload:
    return {}


def _validate_packet_type(packet_type: str) -> None:
    if not packet_type or ":" in packet_type:
        raise ValueError("packet_type must be non-empty and must not contain ':'")


def _validate_day_index(day_index: int | None) -> None:
    if day_index is None:
        return
    if isinstance(day_index, bool) or not isinstance(day_index, int) or day_index <= 0:
        raise ValueError("day_index must be a positive integer or None")


def _validate_item_id(item_id: str) -> None:
    if not isinstance(item_id, str) or not item_id:
        raise ValueError("packet_progress item_id must be a non-empty string")


def _validate_checked(checked: bool) -> None:
    if not isinstance(checked, bool):
        raise ValueError("packet_progress checked must be a boolean")


def _validate_result(result: str) -> None:
    if result not in _RESULT_VALUES:
        raise ValueError("packet_progress result must be one of: correct, partial, uncertain, wrong")


def _validate_confidence(confidence: str) -> None:
    if confidence not in _CONFIDENCE_VALUES:
        raise ValueError("packet_progress confidence must be one of: high, low, medium, unknown")


def confidence_score_to_level(confidence_score: int | None) -> str:
    if confidence_score is None:
        return "unknown"
    _validate_confidence_score(confidence_score)
    if confidence_score <= 2:
        return "low"
    if confidence_score == 3:
        return "medium"
    return "high"


def _validate_confidence_score(confidence_score: int) -> None:
    if (
        isinstance(confidence_score, bool)
        or not isinstance(confidence_score, int)
        or confidence_score < 1
        or confidence_score > 5
    ):
        raise ValueError("packet_progress confidence_score must be an integer from 1 to 5")


def _validate_draft_answer(draft_answer: str) -> None:
    if not isinstance(draft_answer, str):
        raise ValueError("packet_progress draft_answer must be a string")


def _validate_checked_at(checked_at: str) -> None:
    if not isinstance(checked_at, str) or not checked_at:
        raise ValueError("packet_progress checked_at must be a non-empty string")


def _validate_blocker_type(blocker_type: str) -> None:
    if blocker_type not in _BLOCKER_TYPE_VALUES:
        raise ValueError(
            "packet_progress blocker_type must be one of: "
            "application, careless, concept, memory, unknown, visual, wording, "
            "code_gap, concept_connection_gap, math_gap, prerequisite_gap, source_confusion, "
            "terminology_gap, visualization_gap"
        )


def _validate_packet_key(packet_key: str) -> None:
    if ":" not in packet_key:
        _validate_packet_type(packet_key)
        if packet_key not in _NON_DAY_PACKET_TYPES:
            raise ValueError("packet_progress daily packet keys must include a day_index")
        return

    match = _DAY_KEY_PATTERN.fullmatch(packet_key)
    if match is None:
        raise ValueError("packet_progress keys must use the canonical packet namespace")

    _validate_packet_type(match.group("packet_type"))
    _validate_day_index(int(match.group("day_index")))


def build_progress_key(*, packet_type: str, day_index: int | None) -> str:
    _validate_packet_type(packet_type)
    _validate_day_index(day_index)
    if day_index is None:
        if packet_type not in _NON_DAY_PACKET_TYPES:
            raise ValueError("day_index is required for daily packet types")
        return packet_type
    return f"{packet_type}:day:{day_index}"


def normalize_packet_progress(payload: Any) -> PacketProgressPayload:
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError("packet_progress must be a mapping of packet keys to item progress")

    normalized: PacketProgressPayload = {}
    for packet_key, item_progress in payload.items():
        if not isinstance(packet_key, str) or not packet_key:
            raise ValueError("packet_progress keys must be non-empty strings")
        _validate_packet_key(packet_key)
        if not isinstance(item_progress, dict):
            raise ValueError("packet_progress packet entries must be mappings")

        normalized_items: dict[str, PacketProgressItem] = {}
        for item_id, progress in item_progress.items():
            _validate_item_id(item_id)
            if not isinstance(progress, dict):
                raise ValueError("packet_progress item progress must be mappings")

            checked = progress.get("checked")
            _validate_checked(checked)
            normalized_item: PacketProgressItem = {"checked": checked}

            draft_answer = progress.get("draft_answer")
            if draft_answer is not None:
                _validate_draft_answer(draft_answer)
                normalized_item["draft_answer"] = draft_answer

            confidence_score = progress.get("confidence_score")
            if confidence_score is not None:
                _validate_confidence_score(confidence_score)
                normalized_item["confidence_score"] = confidence_score
                normalized_item["confidence"] = confidence_score_to_level(confidence_score)

            checked_at = progress.get("checked_at")
            if checked_at is not None:
                _validate_checked_at(checked_at)
                normalized_item["checked_at"] = checked_at

            result = progress.get("result")
            if result is not None:
                if not isinstance(result, str):
                    raise ValueError("packet_progress result must be a string")
                _validate_result(result)
                normalized_item["result"] = result

            confidence = progress.get("confidence")
            if confidence is not None:
                if not isinstance(confidence, str):
                    raise ValueError("packet_progress confidence must be a string")
                _validate_confidence(confidence)
                if confidence_score is None:
                    normalized_item["confidence"] = confidence

            blocker_type = progress.get("blocker_type")
            if blocker_type is not None:
                if not isinstance(blocker_type, str):
                    raise ValueError("packet_progress blocker_type must be a string")
                _validate_blocker_type(blocker_type)
                normalized_item["blocker_type"] = blocker_type

            normalized_items[item_id] = normalized_item

        normalized[packet_key] = normalized_items
    return normalized


def set_packet_checked(
    payload: PacketProgressPayload,
    *,
    packet_type: str,
    day_index: int | None,
    item_id: str,
    checked: bool,
) -> PacketProgressPayload:
    updated = deepcopy(payload)
    _validate_item_id(item_id)
    _validate_checked(checked)
    progress_key = build_progress_key(packet_type=packet_type, day_index=day_index)
    updated.setdefault(progress_key, {})
    existing = updated[progress_key].get(item_id, {})
    updated[progress_key][item_id] = {**existing, "checked": checked}
    return updated


def set_packet_attempt(
    payload: PacketProgressPayload,
    *,
    packet_type: str,
    day_index: int | None,
    item_id: str,
    draft_answer: str | None = None,
    result: str | None = None,
    confidence: str | None = None,
    confidence_score: int | None = None,
    blocker_type: str | None = None,
    checked_at: str | None = None,
) -> PacketProgressPayload:
    updated = deepcopy(payload)
    _validate_item_id(item_id)
    progress_key = build_progress_key(packet_type=packet_type, day_index=day_index)
    updated.setdefault(progress_key, {})
    existing = updated[progress_key].get(item_id, {"checked": False})
    checked = existing.get("checked", False)
    _validate_checked(checked)
    existing_confidence_score = existing.get("confidence_score")
    if existing_confidence_score is not None:
        _validate_confidence_score(existing_confidence_score)
    next_item: PacketProgressItem = {**existing, "checked": checked}
    if draft_answer is not None:
        _validate_draft_answer(draft_answer)
        next_item["draft_answer"] = draft_answer
    if result is not None:
        _validate_result(result)
        next_item["result"] = result
    if confidence_score is not None:
        _validate_confidence_score(confidence_score)
        next_item["confidence_score"] = confidence_score
        next_item["confidence"] = confidence_score_to_level(confidence_score)
    elif existing_confidence_score is not None:
        next_item["confidence"] = confidence_score_to_level(existing_confidence_score)
    if confidence is not None:
        _validate_confidence(confidence)
        if confidence_score is None and existing_confidence_score is None:
            next_item["confidence"] = confidence
    if blocker_type is not None:
        _validate_blocker_type(blocker_type)
        next_item["blocker_type"] = blocker_type
    if checked_at is not None:
        _validate_checked_at(checked_at)
        next_item["checked_at"] = checked_at
    updated[progress_key][item_id] = next_item
    return updated
