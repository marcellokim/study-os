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
            self.assertTrue(paths.state_dir.is_dir())
            self.assertTrue(paths.manifests_dir.is_dir())
            self.assertTrue(paths.outputs_dir.is_dir())
            self.assertTrue(paths.daily_dir.is_dir())
