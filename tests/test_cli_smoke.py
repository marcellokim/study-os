import subprocess
import sys
import unittest


class CliSmokeTest(unittest.TestCase):
    def test_help_lists_core_commands(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "study_os", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("init-course", completed.stdout)
        self.assertIn("start-day", completed.stdout)
        self.assertIn("close-session", completed.stdout)
        self.assertIn("start-final-recall", completed.stdout)
        self.assertIn("status", completed.stdout)

    def test_empty_invocation_prints_help_and_returns_non_zero(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "study_os"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("usage:", completed.stdout)
        self.assertIn("init-course", completed.stdout)
        self.assertEqual(completed.stderr, "")
