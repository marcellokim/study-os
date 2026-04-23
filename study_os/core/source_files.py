from __future__ import annotations

from pathlib import Path

from study_os.core.models import SourceLink, VisualRequirement
from study_os.core.validation import ValidationError


TEXT_SUFFIXES = frozenset(
    {
        ".csv",
        ".json",
        ".md",
        ".text",
        ".tsv",
        ".txt",
        ".yaml",
        ".yml",
    }
)


def _resolve_workspace_file(workspace_root: Path, relative_path: str, label: str) -> Path:
    raw_path = Path(relative_path)
    if raw_path.is_absolute():
        raise ValidationError(f"{label} path must be relative to the workspace: {relative_path}")

    resolved_workspace = workspace_root.resolve()
    resolved_path = (workspace_root / raw_path).resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_workspace)
    except ValueError as exc:
        raise ValidationError(f"{label} path must stay within the workspace: {relative_path}") from exc
    return resolved_path


def _validate_existing_file(workspace_root: Path, relative_path: str, label: str) -> None:
    path = _resolve_workspace_file(workspace_root, relative_path, label)
    if not path.exists():
        raise ValidationError(f"{label} file not found: {relative_path}")
    if not path.is_file():
        raise ValidationError(f"{label} path must point to a file: {relative_path}")
    if path.stat().st_size == 0:
        raise ValidationError(f"{label} file is empty: {relative_path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if not path.read_bytes().startswith(b"%PDF-"):
            raise ValidationError(f"{label} file does not look like a PDF: {relative_path}")
    elif suffix in TEXT_SUFFIXES:
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError(f"{label} text file must be UTF-8: {relative_path}") from exc


def validate_source_files(
    workspace_root: Path,
    source_manifest: list[SourceLink],
    visual_requirements: list[VisualRequirement],
) -> None:
    for source in source_manifest:
        _validate_existing_file(workspace_root, source.path, "source")

    for visual in visual_requirements:
        if visual.status == "available":
            _validate_existing_file(workspace_root, visual.required_image, "visual requirement")
