import unittest

from study_os.core.models import QueueEntry
from study_os.core.risk_ranking import queue_entry_exam_risk_key


class RiskRankingTest(unittest.TestCase):
    def test_urgent_wrong_item_sorts_before_earlier_generic_high_item(self) -> None:
        generic_earlier = QueueEntry(
            item_id="generic",
            block_id="memory",
            status="R1",
            priority="high",
            last_result="correct",
            confidence="medium",
            next_review_day=1,
            next_review_date="2026-05-21",
            reason="scheduled by state policy",
        )
        urgent_later = QueueEntry(
            item_id="urgent_wrong",
            block_id="uml",
            status="R1",
            priority="urgent",
            last_result="wrong",
            confidence="high",
            next_review_day=2,
            next_review_date="2026-05-22",
            reason="overconfidence, visual pending",
        )

        self.assertEqual(
            [entry.item_id for entry in sorted([generic_earlier, urgent_later], key=queue_entry_exam_risk_key)],
            ["urgent_wrong", "generic"],
        )

    def test_low_confidence_correct_sorts_before_medium_confidence_correct_inside_same_priority(self) -> None:
        medium = QueueEntry(
            item_id="medium",
            block_id="memory",
            status="R1",
            priority="high",
            last_result="correct",
            confidence="medium",
            next_review_day=1,
            next_review_date="2026-05-21",
            reason="scheduled by state policy",
        )
        low = QueueEntry(
            item_id="low",
            block_id="memory",
            status="R1",
            priority="high",
            last_result="correct",
            confidence="low",
            next_review_day=1,
            next_review_date="2026-05-21",
            reason="low confidence",
        )

        self.assertEqual(
            [entry.item_id for entry in sorted([medium, low], key=queue_entry_exam_risk_key)],
            ["low", "medium"],
        )

    def test_high_confidence_wrong_sorts_before_low_confidence_wrong_inside_same_priority(self) -> None:
        low = QueueEntry(
            item_id="low",
            block_id="memory",
            status="R1",
            priority="high",
            last_result="wrong",
            confidence="low",
            next_review_day=1,
            next_review_date="2026-05-21",
            reason="wrong but low confidence",
        )
        high = QueueEntry(
            item_id="high",
            block_id="memory",
            status="R1",
            priority="high",
            last_result="wrong",
            confidence="high",
            next_review_day=1,
            next_review_date="2026-05-21",
            reason="overconfident wrong answer",
        )

        self.assertEqual(
            [entry.item_id for entry in sorted([low, high], key=queue_entry_exam_risk_key)],
            ["high", "low"],
        )
