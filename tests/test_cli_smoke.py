import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
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

    def test_init_course_command_writes_requested_artifacts(self) -> None:
        request = {
            "course": {
                "course_slug": "operating-systems-midterm",
                "course_name": "Operating Systems Midterm",
                "exam_date": "2026-05-20",
                "timezone": "Asia/Seoul",
            },
            "blocks": [
                {
                    "block_id": "use_case_diagram",
                    "block_name": "Use Case Diagram",
                    "block_type": "compare-contrast",
                    "importance": "high",
                    "difficulty": "medium",
                    "exam_relevance": "high",
                    "needs_prereq": False,
                    "needs_visuals": True,
                }
            ],
            "items": [
                {
                    "item_id": "include_vs_extend",
                    "block_id": "use_case_diagram",
                    "prompt": "Explain include vs extend.",
                    "answer_mode": "short-answer",
                    "difficulty": "medium",
                    "exam_relevance": "high",
                    "needs_visuals": True,
                }
            ],
            "visual_requirements": [
                {
                    "item_id": "include_vs_extend",
                    "block_id": "use_case_diagram",
                    "description": "Need the UML arrow direction diagram.",
                    "required_image": "uml-use-case-arrow.png",
                }
            ],
        }

        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            request_file = Path(tmp) / "request.json"
            request_file.write_text(json.dumps(request), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "init-course",
                    "--request-file",
                    str(request_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("applied", completed.stdout)
            self.assertTrue((workspace / "courses" / "operating-systems-midterm" / "course.yaml").exists())
            self.assertTrue((workspace / "courses" / "operating-systems-midterm" / "outputs" / "master_plan.md").exists())
            self.assertIn("operating-systems-midterm", (workspace / "workspace.md").read_text(encoding="utf-8"))

    def test_workspace_without_subcommand_returns_non_zero(self) -> None:
        with TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [sys.executable, "-m", "study_os", "--workspace", tmp],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("command", completed.stderr.lower())
