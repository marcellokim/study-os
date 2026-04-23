import unittest

from study_os.core.models import Block, CourseConfig, Item, QueueEntry, VisualRequirement
from study_os.core.packets import build_final_recall_pack, build_learning_packet, build_master_plan, build_recall_packet


class PacketTest(unittest.TestCase):
    def setUp(self) -> None:
        self.course = CourseConfig(
            course_slug="operating-systems-midterm",
            course_name="Operating Systems Midterm",
            exam_date="2026-05-20",
            timezone="Asia/Seoul",
            current_day=1,
        )
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
        self.visual = VisualRequirement(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            description="Need the use-case arrow direction diagram.",
            required_image="uml-use-case-arrow.png",
        )

    def test_master_plan_mentions_blocks(self) -> None:
        text = build_master_plan(self.course, [self.block], [self.item])
        self.assertIn("Use Case Diagram", text)
        self.assertIn("include_vs_extend", text)

    def test_learning_packet_calls_out_first_action_and_visuals(self) -> None:
        text = build_learning_packet(self.course, 1, [self.block], {"use_case_diagram": [self.item]}, [self.visual])
        self.assertIn("First action", text)
        self.assertIn("uml-use-case-arrow.png", text)

    def test_recall_packet_is_question_first(self) -> None:
        queue_entry = QueueEntry(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            status="R0",
            priority="urgent",
            last_result="wrong",
            confidence="high",
            next_review_day=1,
            next_review_date="2026-04-23",
            reason="comparison confusion",
        )
        text = build_recall_packet(self.course, 1, [queue_entry], {"include_vs_extend": self.item}, [self.visual])
        self.assertIn("Immediate recall", text)
        self.assertIn("Explain include vs extend.", text)

    def test_final_pack_surfaces_risk_items(self) -> None:
        queue_entry = QueueEntry(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            status="FINAL",
            priority="high",
            last_result="wrong",
            confidence="high",
            next_review_day=10,
            next_review_date="2026-05-19",
            reason="overconfidence, visual pending",
        )
        text = build_final_recall_pack(
            self.course,
            [queue_entry],
            {"include_vs_extend": self.item},
            {"use_case_diagram": self.block},
            [self.visual],
        )
        self.assertIn("Mistake-prevention checklist", text)
        self.assertIn("include_vs_extend", text)
