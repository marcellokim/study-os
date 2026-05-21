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

    def test_high_risk_item_gets_exact_urgent_schedule_and_reason(self) -> None:
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
        self.assertEqual(entry.priority, "urgent")
        self.assertEqual(entry.next_review_day, 3)
        self.assertEqual(entry.next_review_date, "2026-04-23")
        self.assertEqual(
            entry.reason,
            "important block, last result wrong, overconfidence, risk error code, visual pending, exam near",
        )

    def test_high_risk_final_item_is_pulled_forward_to_today(self) -> None:
        record = MasteryRecord(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            status="FINAL",
            last_result="wrong",
            last_confidence="high",
        )
        entry = build_queue_entry(
            record,
            self.item,
            self.block,
            "2026-05-20",
            "2026-04-23",
            current_day=7,
            recent_error_codes=["C2"],
            unresolved_visual=True,
        )
        self.assertEqual(entry.priority, "urgent")
        self.assertEqual(entry.next_review_day, 7)
        self.assertEqual(entry.next_review_date, "2026-04-23")
        self.assertEqual(
            entry.reason,
            "important block, last result wrong, overconfidence, risk error code, visual pending",
        )

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

    def test_uncertain_r1_item_is_pulled_forward_to_same_day(self) -> None:
        self._assert_repair_signal_is_pulled_forward("R1", "uncertain")

    def test_partial_r1_item_is_pulled_forward_to_same_day(self) -> None:
        self._assert_repair_signal_is_pulled_forward("R1", "partial")

    def test_uncertain_r2_item_is_pulled_forward_to_same_day(self) -> None:
        self._assert_repair_signal_is_pulled_forward("R2", "uncertain")

    def test_partial_r2_item_is_pulled_forward_to_same_day(self) -> None:
        self._assert_repair_signal_is_pulled_forward("R2", "partial")

    def test_uncertain_final_item_is_pulled_forward_to_same_day(self) -> None:
        self._assert_repair_signal_is_pulled_forward("FINAL", "uncertain")

    def test_partial_final_item_is_pulled_forward_to_same_day(self) -> None:
        self._assert_repair_signal_is_pulled_forward("FINAL", "partial")

    def test_wrong_r2_item_is_pulled_forward_to_same_day(self) -> None:
        self._assert_repair_signal_is_pulled_forward("R2", "wrong")

    def test_low_confidence_correct_r2_item_is_pulled_forward_to_same_day(self) -> None:
        self._assert_repair_signal_is_pulled_forward(
            "R2",
            "correct",
            last_confidence="low",
            expected_reason="important block, low confidence correct",
        )

    def test_low_confidence_correct_final_item_is_pulled_forward_to_same_day(self) -> None:
        self._assert_repair_signal_is_pulled_forward(
            "FINAL",
            "correct",
            last_confidence="low",
            expected_reason="important block, low confidence correct",
        )

    def _assert_repair_signal_is_pulled_forward(
        self,
        status: str,
        last_result: str,
        *,
        last_confidence: str = "medium",
        expected_reason: str | None = None,
    ) -> None:
        record = MasteryRecord(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            status=status,
            last_result=last_result,
            last_confidence=last_confidence,
        )
        entry = build_queue_entry(
            record,
            self.item,
            self.block,
            "2026-05-20",
            "2026-04-23",
            current_day=2,
            recent_error_codes=[],
            unresolved_visual=False,
        )
        self.assertEqual(entry.priority, "high")
        self.assertEqual(entry.next_review_day, 2)
        self.assertEqual(entry.next_review_date, "2026-04-23")
        self.assertEqual(entry.reason, expected_reason or f"important block, last result {last_result}")
