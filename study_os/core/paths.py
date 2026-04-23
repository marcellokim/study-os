from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CoursePaths:
    workspace_root: Path
    course_slug: str
    course_root: Path
    workspace_file: Path
    course_file: Path
    sources_dir: Path
    syllabus_dir: Path
    slides_dir: Path
    transcripts_dir: Path
    images_dir: Path
    notes_dir: Path
    state_dir: Path
    manifests_dir: Path
    outputs_dir: Path
    daily_dir: Path
    blocks_file: Path
    items_file: Path
    mastery_file: Path
    review_queue_file: Path
    error_log_file: Path
    session_history_file: Path
    source_manifest_file: Path
    visual_requirements_file: Path
    master_plan_file: Path
    final_recall_file: Path

    def ensure_directories(self) -> None:
        for path in (
            self.sources_dir,
            self.syllabus_dir,
            self.slides_dir,
            self.transcripts_dir,
            self.images_dir,
            self.notes_dir,
            self.state_dir,
            self.manifests_dir,
            self.outputs_dir,
            self.daily_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def build_course_paths(workspace_root: Path, course_slug: str) -> CoursePaths:
    slug_parts = course_slug.replace("\\", "/").split("/")
    if len(slug_parts) != 1 or any(part in {"", ".", ".."} for part in slug_parts):
        raise ValueError("course_slug must be a simple slug without path separators or dot segments")

    courses_root = workspace_root / "courses"
    course_root = courses_root / course_slug
    resolved_courses_root = courses_root.resolve()
    resolved_course_root = course_root.resolve()
    try:
        resolved_course_root.relative_to(resolved_courses_root)
    except ValueError as exc:
        raise ValueError("course_slug must stay within the courses directory") from exc
    sources_dir = course_root / "sources"
    return CoursePaths(
        workspace_root=workspace_root,
        course_slug=course_slug,
        course_root=course_root,
        workspace_file=workspace_root / "workspace.md",
        course_file=course_root / "course.yaml",
        sources_dir=sources_dir,
        syllabus_dir=sources_dir / "syllabus",
        slides_dir=sources_dir / "slides",
        transcripts_dir=sources_dir / "transcripts",
        images_dir=sources_dir / "images",
        notes_dir=sources_dir / "notes",
        state_dir=course_root / "state",
        manifests_dir=course_root / "manifests",
        outputs_dir=course_root / "outputs",
        daily_dir=course_root / "outputs" / "daily",
        blocks_file=course_root / "state" / "blocks.yaml",
        items_file=course_root / "state" / "items.yaml",
        mastery_file=course_root / "state" / "mastery.json",
        review_queue_file=course_root / "state" / "review_queue.yaml",
        error_log_file=course_root / "state" / "error_log.jsonl",
        session_history_file=course_root / "state" / "session_history.jsonl",
        source_manifest_file=course_root / "manifests" / "source_manifest.yaml",
        visual_requirements_file=course_root / "manifests" / "visual_requirements.yaml",
        master_plan_file=course_root / "outputs" / "master_plan.md",
        final_recall_file=course_root / "outputs" / "final_recall_pack.md",
    )
