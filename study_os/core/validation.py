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
    course_slug = _require_string(course_raw["course_slug"], "course_slug")
    _validate_slug(course_slug, "course_slug")
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
    _require_keys(payload, {"course_slug", "session_date", "reviewed_items"}, "close session request")
    course_slug = _require_string(payload["course_slug"], "course_slug")
    _validate_slug(course_slug, "course_slug")
    session_date = _require_string(payload["session_date"], "session_date")
    _require_iso_date(session_date, "session_date")

    reviewed_items_raw = _require_list(payload["reviewed_items"], "reviewed_items")
    reviewed_items: list[ReviewedItemUpdate] = []
    for raw in reviewed_items_raw:
        _require_keys(raw, {"item_id", "phase", "result"}, "reviewed item")
        item_id = _require_string(raw["item_id"], "item_id")
        if item_id not in known_item_ids:
            raise ValidationError(f"unknown item_id: {item_id}")
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
    if day_index is not None and (
        isinstance(day_index, bool) or not isinstance(day_index, int) or day_index < 1
    ):
        raise ValidationError("day_index must be a positive integer when provided")

    return CloseSessionRequest(
        course_slug=course_slug,
        session_date=session_date,
        reviewed_items=reviewed_items,
        day_index=day_index,
    )
