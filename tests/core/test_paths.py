from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from study_os.core.paths import build_course_paths


class PathsTest(unittest.TestCase):
    def test_ensure_directories_creates_course_layout(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = build_course_paths(Path(tmp), "operating-systems-midterm")
            paths.ensure_directories()

            self.assertTrue(paths.sources_dir.is_dir())
            self.assertTrue(paths.syllabus_dir.is_dir())
            self.assertTrue(paths.slides_dir.is_dir())
            self.assertTrue(paths.transcripts_dir.is_dir())
            self.assertTrue(paths.images_dir.is_dir())
            self.assertTrue(paths.notes_dir.is_dir())
            self.assertTrue(paths.state_dir.is_dir())
            self.assertTrue(paths.manifests_dir.is_dir())
            self.assertTrue(paths.outputs_dir.is_dir())
            self.assertTrue(paths.daily_dir.is_dir())

    def test_build_course_paths_keeps_representative_file_locations(self) -> None:
        workspace_root = Path("/tmp/study-os-workspace")
        course_slug = "operating-systems-midterm"
        paths = build_course_paths(workspace_root, course_slug)
        sources_root = workspace_root / "courses" / course_slug / "sources"
        state_root = workspace_root / "courses" / course_slug / "state"
        outputs_root = workspace_root / "courses" / course_slug / "outputs"

        self.assertEqual(paths.syllabus_dir, sources_root / "syllabus")
        self.assertEqual(paths.slides_dir, sources_root / "slides")
        self.assertEqual(paths.transcripts_dir, sources_root / "transcripts")
        self.assertEqual(paths.images_dir, sources_root / "images")
        self.assertEqual(paths.notes_dir, sources_root / "notes")
        self.assertEqual(paths.review_queue_file, state_root / "review_queue.yaml")
        self.assertEqual(paths.packet_progress_file, state_root / "packet_progress.yaml")
        self.assertEqual(paths.source_manifest_file, workspace_root / "courses" / course_slug / "manifests" / "source_manifest.yaml")
        self.assertEqual(paths.master_plan_file, outputs_root / "master_plan.md")
        self.assertEqual(paths.final_recall_html_file, outputs_root / "final_recall_pack.html")

    def test_daily_packet_html_helpers_build_concrete_paths(self) -> None:
        workspace_root = Path("/tmp/study-os-workspace")
        paths = build_course_paths(workspace_root, "operating-systems-midterm")

        self.assertEqual(
            paths.learning_packet_html_file(day_index=3),
            workspace_root / "courses" / "operating-systems-midterm" / "outputs" / "daily" / "day_03_learning.html",
        )
        self.assertEqual(
            paths.recall_packet_html_file(day_index=12),
            workspace_root / "courses" / "operating-systems-midterm" / "outputs" / "daily" / "day_12_recall.html",
        )
