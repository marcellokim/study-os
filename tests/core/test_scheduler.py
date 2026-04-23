import unittest

from study_os.core.models import Block, Item, MasteryRecord
from study_os.core.scheduler import build_queue_entry


class SchedulerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.block = Block(
            block_id="use_case_diagram",
            block_name="Use Case Diagram",
            block_type="compare-contrast",
            importance="high",
            difficulty="medium",
            exam_relevance="high",
            needs_prereq=False,
            needs_visuals=True,
        )
        self.item = Item(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            prompt="Explain include vs extend.",
            answer_mode="short-answer",
            difficulty="medium",
            exam_relevance="high",
            needs_visuals=True,
        )

    def test_r0_schedules_for_same_day(self) -> None:
        record = MasteryRecord(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            status="R0",
            last_result="correct",
            last_confidence="medium",
        )
        entry = build_queue_entry(
            record,
            self.item,
            self.block,
            "2026-05-20",
            "2026-04-23",
            current_day=1,
            recent_error_codes=[],
            unresolved_visual=False,
        )
        self.assertEqual(entry.next_review_day, 1)
        self.assertEqual(entry.priority, "urgent")

    def test_high_risk_item_gets_escalated_priority(self) -> None:
        record = MasteryRecord(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            status="R2",
            last_result="wrong",
            last_confidence="high",
        )
        entry = build_queue_entry(
            record,
            self.item,
            self.block,
            "2026-04-25",
            "2026-04-23",
            current_day=3,
            recent_error_codes=["C2", "C8"],
            unresolved_visual=True,
        )
        self.assertIn(entry.priority, {"high", "urgent"})
        self.assertIn("visual", entry.reason)

    def test_mastered_item_is_not_queued(self) -> None:
        record = MasteryRecord(item_id="include_vs_extend", block_id="use_case_diagram", status="MASTERED")
        self.assertIsNone(
            build_queue_entry(
                record,
                self.item,
                self.block,
                "2026-05-20",
                "2026-04-23",
                current_day=4,
                recent_error_codes=[],
                unresolved_visual=False,
            )
        )
