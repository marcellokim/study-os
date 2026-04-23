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
        paths = build_course_paths(workspace_root, "operating-systems-midterm")

        self.assertEqual(paths.review_queue_file, workspace_root / "courses" / "operating-systems-midterm" / "state" / "review_queue.yaml")
        self.assertEqual(paths.source_manifest_file, workspace_root / "courses" / "operating-systems-midterm" / "manifests" / "source_manifest.yaml")
        self.assertEqual(paths.master_plan_file, workspace_root / "courses" / "operating-systems-midterm" / "outputs" / "master_plan.md")
