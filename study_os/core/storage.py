from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from study_os.core.json_yaml import append_jsonl, read_json, read_jsonl, read_yamlish, write_json, write_yamlish
from study_os.core.paths import CoursePaths


def _dump(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _dump(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_dump(item) for item in value]
    return value


class CourseStore:
    def __init__(self, paths: CoursePaths) -> None:
        self.paths = paths

    def save_course(self, payload: dict[str, Any]) -> None:
        write_yamlish(self.paths.course_file, _dump(payload))

    def load_course(self) -> dict[str, Any]:
        return read_yamlish(self.paths.course_file, {})

    def save_blocks(self, payload: list[dict[str, Any]]) -> None:
        write_yamlish(self.paths.blocks_file, _dump(payload))

    def load_blocks(self) -> list[dict[str, Any]]:
        return read_yamlish(self.paths.blocks_file, [])

    def save_items(self, payload: list[dict[str, Any]]) -> None:
        write_yamlish(self.paths.items_file, _dump(payload))

    def load_items(self) -> list[dict[str, Any]]:
        return read_yamlish(self.paths.items_file, [])

    def save_source_manifest(self, payload: list[dict[str, Any]]) -> None:
        write_yamlish(self.paths.source_manifest_file, _dump(payload))

    def load_source_manifest(self) -> list[dict[str, Any]]:
        return read_yamlish(self.paths.source_manifest_file, [])

    def save_visual_requirements(self, payload: list[dict[str, Any]]) -> None:
        write_yamlish(self.paths.visual_requirements_file, _dump(payload))

    def load_visual_requirements(self) -> list[dict[str, Any]]:
        return read_yamlish(self.paths.visual_requirements_file, [])

    def save_mastery(self, payload: dict[str, dict[str, Any]]) -> None:
        write_json(self.paths.mastery_file, _dump(payload))

    def load_mastery(self) -> dict[str, dict[str, Any]]:
        return read_json(self.paths.mastery_file, {})

    def save_review_queue(self, payload: list[dict[str, Any]]) -> None:
        write_yamlish(self.paths.review_queue_file, _dump(payload))

    def load_review_queue(self) -> list[dict[str, Any]]:
        return read_yamlish(self.paths.review_queue_file, [])

    def append_error(self, payload: dict[str, Any]) -> None:
        append_jsonl(self.paths.error_log_file, _dump(payload))

    def load_errors(self) -> list[dict[str, Any]]:
        return read_jsonl(self.paths.error_log_file)

    def append_session_history(self, payload: dict[str, Any]) -> None:
        append_jsonl(self.paths.session_history_file, _dump(payload))

    def load_session_history(self) -> list[dict[str, Any]]:
        return read_jsonl(self.paths.session_history_file)
