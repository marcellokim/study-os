import unittest

from study_os.core.models import MasteryRecord, ReviewedItemUpdate
from study_os.core.transitions import apply_review_update


class TransitionTest(unittest.TestCase):
    def test_learning_success_enters_same_day_recall(self) -> None:
        record = MasteryRecord(item_id="include_vs_extend", block_id="use_case_diagram")
        update = ReviewedItemUpdate(
            item_id="include_vs_extend",
            phase="learning",
            result="correct",
            confidence="medium",
        )

        new_record = apply_review_update(record, update, "2026-04-23")
        self.assertEqual(new_record.status, "R0")
        self.assertEqual(new_record.last_review_date, "2026-04-23")

    def test_correct_review_promotes_one_step(self) -> None:
        record = MasteryRecord(item_id="include_vs_extend", block_id="use_case_diagram", status="R1")
        update = ReviewedItemUpdate(item_id="include_vs_extend", phase="review", result="correct", confidence="high")
        self.assertEqual(apply_review_update(record, update, "2026-04-23").status, "R2")

    def test_high_confidence_wrong_regresses_two_steps_without_risk_code(self) -> None:
        record = MasteryRecord(item_id="include_vs_extend", block_id="use_case_diagram", status="R2")
        update = ReviewedItemUpdate(item_id="include_vs_extend", phase="review", result="wrong", confidence="high")
        self.assertEqual(apply_review_update(record, update, "2026-04-23").status, "R0")

    def test_risk_code_wrong_regresses_two_steps_without_high_confidence(self) -> None:
        record = MasteryRecord(item_id="include_vs_extend", block_id="use_case_diagram", status="R2")
        update = ReviewedItemUpdate(
            item_id="include_vs_extend",
            phase="review",
            result="wrong",
            confidence="medium",
            error_code="C2",
        )
        self.assertEqual(apply_review_update(record, update, "2026-04-23").status, "R0")

    def test_low_confidence_correct_holds_position(self) -> None:
        record = MasteryRecord(item_id="include_vs_extend", block_id="use_case_diagram", status="FINAL")
        update = ReviewedItemUpdate(item_id="include_vs_extend", phase="review", result="correct", confidence="low")
        self.assertEqual(apply_review_update(record, update, "2026-04-23").status, "FINAL")

    def test_partial_review_regresses_one_step(self) -> None:
        record = MasteryRecord(item_id="include_vs_extend", block_id="use_case_diagram", status="R2")
        update = ReviewedItemUpdate(item_id="include_vs_extend", phase="review", result="partial", confidence="medium")

        new_record = apply_review_update(record, update, "2026-04-23")
        self.assertEqual(new_record.status, "R1")
        self.assertEqual(new_record.consecutive_successes, 0)

    def test_uncertain_review_holds_position_and_resets_successes(self) -> None:
        record = MasteryRecord(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            status="R2",
            consecutive_successes=3,
        )
        update = ReviewedItemUpdate(item_id="include_vs_extend", phase="review", result="uncertain", confidence="medium")

        new_record = apply_review_update(record, update, "2026-04-23")
        self.assertEqual(new_record.status, "R2")
        self.assertEqual(new_record.consecutive_successes, 0)
        self.assertEqual(new_record.last_review_date, "2026-04-23")

    def test_partial_review_does_not_regress_below_r0(self) -> None:
        record = MasteryRecord(item_id="include_vs_extend", block_id="use_case_diagram", status="R0")
        update = ReviewedItemUpdate(item_id="include_vs_extend", phase="review", result="partial", confidence="medium")
        self.assertEqual(apply_review_update(record, update, "2026-04-23").status, "R0")

    def test_correct_review_does_not_promote_past_mastered(self) -> None:
        record = MasteryRecord(item_id="include_vs_extend", block_id="use_case_diagram", status="MASTERED")
        update = ReviewedItemUpdate(item_id="include_vs_extend", phase="review", result="correct", confidence="high")
        self.assertEqual(apply_review_update(record, update, "2026-04-23").status, "MASTERED")
