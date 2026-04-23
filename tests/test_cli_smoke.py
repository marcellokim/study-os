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

    def test_start_day_command_writes_daily_packets_and_reports_success(self) -> None:
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

            init_completed = subprocess.run(
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
            self.assertEqual(init_completed.returncode, 0, init_completed.stderr)

            review_queue_file = workspace / "courses" / "operating-systems-midterm" / "state" / "review_queue.yaml"
            review_queue_file.write_text(
                json.dumps(
                    [
                        {
                            "item_id": "include_vs_extend",
                            "block_id": "use_case_diagram",
                            "status": "R0",
                            "priority": "urgent",
                            "last_result": "wrong",
                            "confidence": "high",
                            "next_review_day": 1,
                            "next_review_date": "2026-04-23",
                            "reason": "comparison confusion",
                        }
                    ],
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "start-day",
                    "--course",
                    "operating-systems-midterm",
                    "--day",
                    "1",
                    "--today",
                    "2026-04-23",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            learning_file = workspace / "courses" / "operating-systems-midterm" / "outputs" / "daily" / "day_01_learning.md"
            recall_file = workspace / "courses" / "operating-systems-midterm" / "outputs" / "daily" / "day_01_recall.md"
            course_file = workspace / "courses" / "operating-systems-midterm" / "course.yaml"

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("applied", completed.stdout)
            self.assertIn(str(learning_file), completed.stdout)
            self.assertIn(str(recall_file), completed.stdout)
            self.assertIn(str(course_file), completed.stdout)
            self.assertTrue(learning_file.exists())
            self.assertTrue(recall_file.exists())
            self.assertIn("2026-04-23", learning_file.read_text(encoding="utf-8"))
            self.assertIn("2026-04-23", recall_file.read_text(encoding="utf-8"))
            self.assertIn('"current_day": 1', course_file.read_text(encoding="utf-8"))

    def test_start_day_unknown_course_fails_cleanly_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "start-day",
                    "--course",
                    "missing-course",
                    "--day",
                    "1",
                    "--today",
                    "2026-04-23",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            self.assertIn("error: unknown course_slug: missing-course", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)
            self.assertFalse((workspace / "courses" / "missing-course").exists())

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
