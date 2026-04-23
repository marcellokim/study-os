from __future__ import annotations

from datetime import date
import re

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
_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _require_keys(payload: object, keys: set[str], label: str) -> None:
    if not isinstance(payload, dict):
        raise ValidationError(f"{label} must be an object")
    missing = keys.difference(payload)
    if missing:
        raise ValidationError(f"{label} is missing keys: {sorted(missing)}")


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a string")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{label} must be a boolean")
    return value


def _require_list(value: object, label: str) -> list:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be a list")
    return value


def _require_optional_string(value: object, label: str, default: str = "") -> str:
    if value is None:
        return default
    return _require_string(value, label)


def validate_iso_date_text(value: object, label: str) -> str:
    text = _require_string(value, label)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{label} must be YYYY-MM-DD") from exc
    return text


def _require_iso_date(value: object, label: str) -> None:
    validate_iso_date_text(value, label)


def validate_positive_day_index(value: object, label: str = "day_index") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationError(f"{label} must be a positive integer")
    return value


def _validate_slug(value: object, label: str) -> str:
    text = _require_string(value, label)
    if not _SLUG_PATTERN.fullmatch(text):
        raise ValidationError(f"{label} must be a lowercase slug using only letters, digits, _ or -")
    return text


def validate_course_slug_text(value: object, label: str = "course_slug") -> str:
    return _validate_slug(value, label)


def validate_init_course_request(payload: dict) -> InitCourseRequest:
    _require_keys(payload, {"course", "blocks", "items"}, "init request")

    course_raw = payload["course"]
    _require_keys(course_raw, {"course_slug", "course_name", "exam_date", "timezone"}, "course")
    course_slug = validate_course_slug_text(course_raw["course_slug"], "course_slug")
    course_name = _require_string(course_raw["course_name"], "course_name")
    exam_date = _require_string(course_raw["exam_date"], "exam_date")
    _require_iso_date(exam_date, "exam_date")
    timezone = _require_string(course_raw["timezone"], "timezone")
    course = CourseConfig(
        course_slug=course_slug,
        course_name=course_name,
        exam_date=exam_date,
        timezone=timezone,
    )

    blocks_raw = _require_list(payload["blocks"], "blocks")
    blocks: list[Block] = []
    seen_block_ids: set[str] = set()
    for raw in blocks_raw:
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
        block_id = _require_string(raw["block_id"], "block_id")
        if block_id in seen_block_ids:
            raise ValidationError(f"duplicate block_id: {block_id}")
        seen_block_ids.add(block_id)
        block_name = _require_string(raw["block_name"], "block_name")
        block_type = _require_string(raw["block_type"], "block_type")
        importance = _require_string(raw["importance"], "importance")
        difficulty = _require_string(raw["difficulty"], "difficulty")
        exam_relevance = _require_string(raw["exam_relevance"], "exam_relevance")
        needs_prereq = _require_bool(raw["needs_prereq"], "needs_prereq")
        needs_visuals = _require_bool(raw["needs_visuals"], "needs_visuals")
        blocks.append(
            Block(
                block_id=block_id,
                block_name=block_name,
                block_type=block_type,
                importance=importance,
                difficulty=difficulty,
                exam_relevance=exam_relevance,
                needs_prereq=needs_prereq,
                needs_visuals=needs_visuals,
            )
        )

    block_ids = {block.block_id for block in blocks}
    items_raw = _require_list(payload["items"], "items")
    items: list[Item] = []
    seen_item_ids: set[str] = set()
    for raw in items_raw:
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
        item_id = _require_string(raw["item_id"], "item_id")
        if item_id in seen_item_ids:
            raise ValidationError(f"duplicate item_id: {item_id}")
        seen_item_ids.add(item_id)
        block_id = _require_string(raw["block_id"], "block_id")
        prompt = _require_string(raw["prompt"], "prompt")
        answer_mode = _require_string(raw["answer_mode"], "answer_mode")
        difficulty = _require_string(raw["difficulty"], "difficulty")
        exam_relevance = _require_string(raw["exam_relevance"], "exam_relevance")
        needs_visuals = _require_bool(raw["needs_visuals"], "needs_visuals")
        if block_id not in block_ids:
            raise ValidationError(f"item {item_id} references unknown block {block_id}")
        items.append(
            Item(
                item_id=item_id,
                block_id=block_id,
                prompt=prompt,
                answer_mode=answer_mode,
                difficulty=difficulty,
                exam_relevance=exam_relevance,
                needs_visuals=needs_visuals,
            )
        )

    item_ids = {item.item_id for item in items}
    item_block_ids = {item.item_id: item.block_id for item in items}
    source_manifest_raw = _require_list(payload.get("source_manifest", []), "source_manifest")
    source_manifest: list[SourceLink] = []
    for raw in source_manifest_raw:
        _require_keys(raw, {"block_id", "source_type", "path"}, "source manifest row")
        block_id = _require_string(raw["block_id"], "block_id")
        source_type = _require_string(raw["source_type"], "source_type")
        path = _require_string(raw["path"], "path")
        note = _require_optional_string(raw.get("note"), "note")
        if block_id not in block_ids:
            raise ValidationError(f"unknown source block_id: {block_id}")
        source_manifest.append(
            SourceLink(
                block_id=block_id,
                source_type=source_type,
                path=path,
                note=note,
            )
        )

    visual_requirements_raw = _require_list(payload.get("visual_requirements", []), "visual_requirements")
    visual_requirements: list[VisualRequirement] = []
    for raw in visual_requirements_raw:
        _require_keys(raw, {"item_id", "block_id", "description", "required_image"}, "visual requirement")
        item_id = _require_string(raw["item_id"], "item_id")
        block_id = _require_string(raw["block_id"], "block_id")
        description = _require_string(raw["description"], "description")
        required_image = _require_string(raw["required_image"], "required_image")
        status = _require_optional_string(raw.get("status"), "status", default="missing")
        if item_id not in item_ids:
            raise ValidationError(f"unknown visual item_id: {item_id}")
        if block_id not in block_ids:
            raise ValidationError(f"unknown visual block_id: {block_id}")
        expected_block_id = item_block_ids[item_id]
        if block_id != expected_block_id:
            raise ValidationError(
                f"visual requirement item {item_id} must use block_id {expected_block_id}, got {block_id}"
            )
        visual_requirements.append(
            VisualRequirement(
                item_id=item_id,
                block_id=block_id,
                description=description,
                required_image=required_image,
                status=status,
            )
        )

    return InitCourseRequest(
        course=course,
        blocks=blocks,
        items=items,
        source_manifest=source_manifest,
        visual_requirements=visual_requirements,
    )


def validate_close_session_request(payload: dict, known_item_ids: set[str]) -> CloseSessionRequest:
    request = validate_close_session_request_shape(payload)
    for reviewed in request.reviewed_items:
        if reviewed.item_id not in known_item_ids:
            raise ValidationError(f"unknown item_id: {reviewed.item_id}")
    return request


def validate_close_session_request_shape(payload: dict) -> CloseSessionRequest:
    _require_keys(payload, {"course_slug", "session_date", "reviewed_items"}, "close session request")
    course_slug = validate_course_slug_text(payload["course_slug"], "course_slug")
    session_date = _require_string(payload["session_date"], "session_date")
    _require_iso_date(session_date, "session_date")

    reviewed_items_raw = _require_list(payload["reviewed_items"], "reviewed_items")
    reviewed_items: list[ReviewedItemUpdate] = []
    seen_item_ids: set[str] = set()
    for raw in reviewed_items_raw:
        _require_keys(raw, {"item_id", "phase", "result"}, "reviewed item")
        item_id = _require_string(raw["item_id"], "item_id")
        if item_id in seen_item_ids:
            raise ValidationError(f"duplicate reviewed_items item_id: {item_id}")
        seen_item_ids.add(item_id)

        phase = _require_string(raw["phase"], "phase")
        if phase not in {"learning", "review"}:
            raise ValidationError(f"unsupported phase: {phase}")

        result = _require_string(raw["result"], "result")
        if result not in _RESULT_VALUES:
            raise ValidationError(f"unsupported result: {result}")

        confidence = _require_string(raw.get("confidence", Confidence.UNKNOWN.value), "confidence")
        if confidence not in _CONFIDENCE_VALUES:
            raise ValidationError(f"unsupported confidence: {confidence}")

        error_code = raw.get("error_code")
        if error_code is not None:
            error_code = _require_string(error_code, "error_code")
            if error_code not in _ERROR_CODE_VALUES:
                raise ValidationError(f"unsupported error_code: {error_code}")

        note = _require_optional_string(raw.get("note"), "note")
        reviewed_items.append(
            ReviewedItemUpdate(
                item_id=item_id,
                phase=phase,
                result=result,
                confidence=confidence,
                error_code=error_code,
                note=note,
            )
        )

    day_index = payload.get("day_index")
    if day_index is not None:
        try:
            day_index = validate_positive_day_index(day_index)
        except ValidationError as exc:
            raise ValidationError("day_index must be a positive integer when provided") from exc

    return CloseSessionRequest(
        course_slug=course_slug,
        session_date=session_date,
        reviewed_items=reviewed_items,
        day_index=day_index,
    )
