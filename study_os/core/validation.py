from __future__ import annotations

from datetime import date

from study_os.core.constants import Confidence, ErrorCode, Result
from study_os.core.models import (
    Block,
    CloseSessionRequest,
    CourseConfig,
    InitCourseRequest,
    Item,
    ReviewedItemUpdate,
    SourceLink,
    VisualRequirement,
)


class ValidationError(ValueError):
    pass


_RESULT_VALUES = {result.value for result in Result}
_CONFIDENCE_VALUES = {level.value for level in Confidence}
_ERROR_CODE_VALUES = {code.value for code in ErrorCode}


def _require_keys(payload: dict, keys: set[str], label: str) -> None:
    missing = keys.difference(payload)
    if missing:
        raise ValidationError(f"{label} is missing keys: {sorted(missing)}")


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a string")
    return value


def _require_iso_date(value: object, label: str) -> None:
    text = _require_string(value, label)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{label} must be YYYY-MM-DD") from exc


def _validate_slug(value: object, label: str) -> None:
    text = _require_string(value, label)
    if not text or any(ch.isspace() for ch in text):
        raise ValidationError(f"{label} must be a non-empty slug without spaces")


def validate_init_course_request(payload: dict) -> InitCourseRequest:
    _require_keys(payload, {"course", "blocks", "items"}, "init request")

    course_raw = payload["course"]
    _require_keys(course_raw, {"course_slug", "course_name", "exam_date", "timezone"}, "course")
    _validate_slug(course_raw["course_slug"], "course_slug")
    _require_string(course_raw["course_name"], "course_name")
    _require_iso_date(course_raw["exam_date"], "exam_date")
    _require_string(course_raw["timezone"], "timezone")
    course = CourseConfig(**course_raw)

    blocks: list[Block] = []
    for raw in payload["blocks"]:
        _require_keys(
            raw,
            {
                "block_id",
                "block_name",
                "block_type",
                "importance",
                "difficulty",
                "exam_relevance",
                "needs_prereq",
                "needs_visuals",
            },
            "block",
        )
        blocks.append(Block(**raw))

    block_ids = {block.block_id for block in blocks}
    items: list[Item] = []
    for raw in payload["items"]:
        _require_keys(
            raw,
            {
                "item_id",
                "block_id",
                "prompt",
                "answer_mode",
                "difficulty",
                "exam_relevance",
                "needs_visuals",
            },
            "item",
        )
        if raw["block_id"] not in block_ids:
            raise ValidationError(f"item {raw['item_id']} references unknown block {raw['block_id']}")
        items.append(Item(**raw))

    item_ids = {item.item_id for item in items}
    source_manifest = [SourceLink(**raw) for raw in payload.get("source_manifest", [])]

    visual_requirements: list[VisualRequirement] = []
    for raw in payload.get("visual_requirements", []):
        _require_keys(raw, {"item_id", "block_id", "description", "required_image"}, "visual requirement")
        if raw["item_id"] not in item_ids:
            raise ValidationError(f"unknown visual item_id: {raw['item_id']}")
        if raw["block_id"] not in block_ids:
            raise ValidationError(f"unknown visual block_id: {raw['block_id']}")
        visual_requirements.append(VisualRequirement(**raw))

    return InitCourseRequest(
        course=course,
        blocks=blocks,
        items=items,
        source_manifest=source_manifest,
        visual_requirements=visual_requirements,
    )


def validate_close_session_request(payload: dict, known_item_ids: set[str]) -> CloseSessionRequest:
    _require_keys(payload, {"course_slug", "session_date", "reviewed_items"}, "close session request")
    _validate_slug(payload["course_slug"], "course_slug")
    _require_iso_date(payload["session_date"], "session_date")

    reviewed_items: list[ReviewedItemUpdate] = []
    for raw in payload["reviewed_items"]:
        _require_keys(raw, {"item_id", "phase", "result"}, "reviewed item")
        if raw["item_id"] not in known_item_ids:
            raise ValidationError(f"unknown item_id: {raw['item_id']}")
        phase = _require_string(raw["phase"], "phase")
        if phase not in {"learning", "review"}:
            raise ValidationError(f"unsupported phase: {phase}")

        result = _require_string(raw["result"], "result")
        if result not in _RESULT_VALUES:
            raise ValidationError(f"unsupported result: {result}")

        confidence = raw.get("confidence", Confidence.UNKNOWN.value)
        confidence = _require_string(confidence, "confidence")
        if confidence not in _CONFIDENCE_VALUES:
            raise ValidationError(f"unsupported confidence: {confidence}")

        error_code = raw.get("error_code")
        if error_code is not None:
            error_code = _require_string(error_code, "error_code")
            if error_code not in _ERROR_CODE_VALUES:
                raise ValidationError(f"unsupported error_code: {error_code}")

        reviewed_items.append(ReviewedItemUpdate(**raw))

    day_index = payload.get("day_index")
    if day_index is not None and (
        isinstance(day_index, bool) or not isinstance(day_index, int) or day_index < 1
    ):
        raise ValidationError("day_index must be a positive integer when provided")

    return CloseSessionRequest(
        course_slug=payload["course_slug"],
        session_date=payload["session_date"],
        reviewed_items=reviewed_items,
        day_index=day_index,
    )
