from __future__ import annotations

import unittest

from study_os.core.close_session_draft import build_close_session_draft
from study_os.core.models import Item


class CloseSessionDraftTest(unittest.TestCase):
    def setUp(self) -> None:
        self.items = {
            "uml_fix": Item(
                item_id="uml_fix",
                block_id="uml",
                prompt="Fix the UML relation.",
                answer_mode="short-answer",
                difficulty="medium",
                exam_relevance="high",
                needs_visuals=True,
            ),
            "array_trace": Item(
                item_id="array_trace",
                block_id="arrays",
                prompt="Trace the array output.",
                answer_mode="short-answer",
                difficulty="medium",
                exam_relevance="high",
                needs_visuals=False,
            ),
            "memory_gap": Item(
                item_id="memory_gap",
                block_id="arrays",
                prompt="Recall array indexing.",
                answer_mode="short-answer",
                difficulty="medium",
                exam_relevance="high",
                needs_visuals=False,
            ),
        }

    def test_builds_reviewed_items_from_packet_attempts(self) -> None:
        draft = build_close_session_draft(
            course_slug="basic-computer-programming-final",
            session_date="2026-05-21",
            packet_type="recall",
            day_index=1,
            packet_progress={
                "recall:day:1": {
                    "uml_fix": {
                        "checked": True,
                        "draft_answer": "Wrong arrow direction.",
                        "result": "wrong",
                        "confidence_score": 5,
                        "confidence": "high",
                        "blocker_type": "visual",
                    },
                    "array_trace": {
                        "checked": True,
                        "draft_answer": "I got the output but was unsure.",
                        "result": "correct",
                        "confidence_score": 2,
                        "confidence": "low",
                        "blocker_type": "careless",
                    },
                }
            },
            items_by_id=self.items,
        )

        self.assertEqual(draft["course_slug"], "basic-computer-programming-final")
        self.assertEqual(draft["session_date"], "2026-05-21")
        self.assertEqual(draft["day_index"], 1)
        self.assertEqual(
            draft["reviewed_items"],
            [
                {
                    "item_id": "array_trace",
                    "phase": "review",
                    "result": "correct",
                    "confidence": "low",
                    "note": "blocker=careless; answer=I got the output but was unsure.",
                },
                {
                    "item_id": "uml_fix",
                    "phase": "review",
                    "result": "wrong",
                    "confidence": "high",
                    "error_code": "C6",
                    "note": "blocker=visual; answer=Wrong arrow direction.",
                },
            ],
        )
        self.assertEqual(draft["next_focus"], ["array_trace", "uml_fix"])

    def test_learning_packet_uses_learning_phase_and_maps_confidence_score(self) -> None:
        draft = build_close_session_draft(
            course_slug="course",
            session_date="2026-05-21",
            packet_type="learning",
            day_index=1,
            packet_progress={
                "learning:day:1": {
                    "memory_gap": {
                        "checked": True,
                        "draft_answer": "Forgot the base case.",
                        "result": "partial",
                        "confidence_score": 3,
                        "blocker_type": "memory",
                    }
                }
            },
            items_by_id=self.items,
        )

        self.assertEqual(
            draft["reviewed_items"],
            [
                {
                    "item_id": "memory_gap",
                    "phase": "learning",
                    "result": "partial",
                    "confidence": "medium",
                    "error_code": "C1",
                    "note": "blocker=memory; answer=Forgot the base case.",
                }
            ],
        )
        self.assertEqual(draft["next_focus"], ["memory_gap"])

    def test_ignores_items_without_result_unknown_result_or_missing_item(self) -> None:
        draft = build_close_session_draft(
            course_slug="course",
            session_date="2026-05-21",
            packet_type="learning",
            day_index=1,
            packet_progress={
                "learning:day:1": {
                    "array_trace": {"checked": True, "draft_answer": "answer"},
                    "memory_gap": {"checked": True, "result": "skipped"},
                    "missing": {"checked": True, "result": "wrong"},
                }
            },
            items_by_id=self.items,
        )

        self.assertEqual(draft["reviewed_items"], [])
        self.assertEqual(draft["next_focus"], [])
