from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


def _read_json_file(path: Path, default: JsonValue) -> JsonValue:
    if not path.exists():
        return copy.deepcopy(default)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return copy.deepcopy(default)
    return json.loads(text)


def _write_json_file(path: Path, payload: JsonValue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_yamlish(path: Path, default: JsonValue) -> JsonValue:
    return _read_json_file(path, default)


def write_yamlish(path: Path, payload: JsonValue) -> None:
    _write_json_file(path, payload)


def read_json(path: Path, default: JsonValue) -> JsonValue:
    return _read_json_file(path, default)


def write_json(path: Path, payload: JsonValue) -> None:
    _write_json_file(path, payload)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows
