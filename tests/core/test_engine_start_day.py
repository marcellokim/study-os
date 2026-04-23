from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from study_os.core.engine import StudyEngine
from study_os.core.models import MasteryRecord
from study_os.core.paths import build_course_paths
from study_os.core.storage import CourseStore


class StartDayWorkflowTest(unittest.TestCase):
    def test_start_day_writes_learning_and_recall_packets(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(
                {
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
            )

            paths = build_course_paths(Path(tmp), "operating-systems-midterm")
            store = CourseStore(paths)
            store.save_mastery(
                {
                    "include_vs_extend": asdict(
                        MasteryRecord(
                            item_id="include_vs_extend",
                            block_id="use_case_diagram",
                            status="R0",
                            last_result="wrong",
                            last_confidence="high",
                        )
                    )
                }
            )
            store.save_review_queue(
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
                ]
            )

            receipt = engine.start_day("operating-systems-midterm", day_index=1, today="2026-04-23")
            self.assertEqual(receipt.status, "applied")
            self.assertTrue(paths.daily_dir.joinpath("day_01_learning.md").exists())
            self.assertTrue(paths.daily_dir.joinpath("day_01_recall.md").exists())
            self.assertIn("First action", paths.daily_dir.joinpath("day_01_learning.md").read_text(encoding="utf-8"))
            self.assertIn("Immediate recall", paths.daily_dir.joinpath("day_01_recall.md").read_text(encoding="utf-8"))
