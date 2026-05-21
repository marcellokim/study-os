from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from study_os.core.engine import StudyEngine
from study_os.core.models import MasteryRecord
from study_os.core.paths import build_course_paths
from study_os.core.storage import CourseStore


class FinalRecallWorkflowTest(unittest.TestCase):
    def test_start_final_recall_writes_pack_and_status_summary(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(
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
                            status="FINAL",
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
                        "status": "FINAL",
                        "priority": "high",
                        "last_result": "wrong",
                        "confidence": "high",
                        "next_review_day": 3,
                        "next_review_date": "2026-04-24",
                        "reason": "overconfidence, visual pending",
                    }
                ]
            )
            store.save_packet_progress({"final_recall": {"include_vs_extend": {"checked": True}}})

            receipt = engine.start_final_recall("operating-systems-midterm", today="2026-04-23")
            summary = engine.status("operating-systems-midterm")
            pack_text = paths.final_recall_file.read_text(encoding="utf-8")
            html_text = paths.final_recall_html_file.read_text(encoding="utf-8")

            self.assertEqual(receipt.status, "applied")
            self.assertTrue(paths.final_recall_file.exists())
            self.assertTrue(paths.final_recall_html_file.exists())
            self.assertIn(str(paths.final_recall_html_file), receipt.generated_files)
            self.assertIn("최종 회상 팩", pack_text)
            self.assertIn("- 생성일: 2026-04-23", pack_text)
            self.assertIn('body data-packet-type="final_recall"', html_text)
            self.assertIn('data-item-id="include_vs_extend" checked', html_text)
            self.assertIn("include_vs_extend", summary)
            self.assertIn("FINAL", summary)
            self.assertIn("Checked packet entries: 1", summary)

    def test_start_final_recall_includes_available_visuals_in_pack(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(
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
                    "visual_requirements": [
                        {
                            "item_id": "include_vs_extend",
                            "block_id": "use_case_diagram",
                            "description": "Need the UML arrow direction diagram.",
                            "required_image": (
                                "courses/operating-systems-midterm/sources/images/uml-use-case-arrow.png"
                            ),
                            "status": "available",
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
                            status="FINAL",
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
                        "status": "FINAL",
                        "priority": "high",
                        "last_result": "wrong",
                        "confidence": "high",
                        "next_review_day": 3,
                        "next_review_date": "2026-04-24",
                        "reason": "overconfidence",
                    }
                ]
            )

            engine.start_final_recall("operating-systems-midterm", today="2026-04-23")

            pack_text = paths.final_recall_file.read_text(encoding="utf-8")
            html_text = paths.final_recall_html_file.read_text(encoding="utf-8")

            self.assertIn("## 필요한 시각자료", pack_text)
            self.assertIn(
                "- `include_vs_extend`: "
                "`courses/operating-systems-midterm/sources/images/uml-use-case-arrow.png` "
                "(status: available)",
                pack_text,
            )
            self.assertIn(
                'src="/assets/courses/operating-systems-midterm/sources/images/uml-use-case-arrow.png"',
                html_text,
            )
