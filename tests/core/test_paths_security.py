from pathlib import Path
import unittest

from study_os.core.paths import build_course_paths


class PathSecurityTest(unittest.TestCase):
    def test_build_course_paths_rejects_course_slug_that_escapes_courses_directory(self) -> None:
        workspace_root = Path('/tmp/study-os-workspace')

        with self.assertRaisesRegex(ValueError, 'course_slug must stay within the courses directory'):
            build_course_paths(workspace_root, '../escape')
