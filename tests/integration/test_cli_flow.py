import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


class CliFlowIntegrationTest(unittest.TestCase):
    def test_full_cli_flow(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            request_file = workspace / "init_request.json"
            request_file.write_text(
                json.dumps(
                    {
                        "course": {
                            "course_slug": "operating-systems-midterm",
                            "course_name": "Operating Systems Midterm",
                            "exam_date": "2026-04-25",
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
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            close_request = workspace / "close_request.json"
            close_request.write_text(
                json.dumps(
                    {
                        "course_slug": "operating-systems-midterm",
                        "session_date": "2026-04-23",
                        "day_index": 1,
                        "reviewed_items": [
                            {
                                "item_id": "include_vs_extend",
                                "phase": "learning",
                                "result": "correct",
                                "confidence": "medium",
                                "note": "First pass complete.",
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            commands = [
                [sys.executable, "-m", "study_os", "--workspace", str(workspace), "init-course", "--request-file", str(request_file)],
                [sys.executable, "-m", "study_os", "--workspace", str(workspace), "start-day", "--course", "operating-systems-midterm", "--day", "1", "--today", "2026-04-23"],
                [sys.executable, "-m", "study_os", "--workspace", str(workspace), "close-session", "--request-file", str(close_request)],
                [sys.executable, "-m", "study_os", "--workspace", str(workspace), "start-final-recall", "--course", "operating-systems-midterm", "--today", "2026-04-23"],
                [sys.executable, "-m", "study_os", "--workspace", str(workspace), "status", "--course", "operating-systems-midterm"],
            ]

            outputs: list[str] = []
            for command in commands:
                completed = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                outputs.append(completed.stdout)

            final_recall_file = workspace.joinpath("courses/operating-systems-midterm/outputs/final_recall_pack.md")
            self.assertIn("applied", outputs[3])
            self.assertIn(str(final_recall_file), outputs[3])
            self.assertIn("Course: operating-systems-midterm", outputs[4])
            self.assertIn("- include_vs_extend [R0]", outputs[4])
            self.assertTrue(final_recall_file.exists())
