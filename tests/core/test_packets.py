import unittest
from textwrap import dedent

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
        self.other_block = Block(
            block_id="cpu_scheduling",
            block_name="CPU Scheduling",
            block_type="mechanism",
            importance="medium",
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
        self.other_item = Item(
            item_id="context_switch",
            block_id="cpu_scheduling",
            prompt="Explain context-switch overhead.",
            answer_mode="short-answer",
            difficulty="medium",
            exam_relevance="high",
            needs_visuals=False,
        )
        self.third_item = Item(
            item_id="round_robin",
            block_id="cpu_scheduling",
            prompt="Explain round-robin fairness.",
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
        self.other_visual = VisualRequirement(
            item_id="round_robin",
            block_id="cpu_scheduling",
            description="Need the scheduling timeline diagram.",
            required_image="cpu-gantt-chart.png",
        )

    def test_master_plan_mentions_blocks(self) -> None:
        text = build_master_plan(self.course, [self.block], [self.item])
        self.assertIn("Use Case Diagram", text)
        self.assertIn("include_vs_extend", text)

    def test_learning_packet_renders_canonical_markdown_from_shuffled_inputs(self) -> None:
        text = build_learning_packet(
            self.course,
            1,
            [self.block, self.other_block],
            {
                "use_case_diagram": [self.item],
                "cpu_scheduling": [self.third_item, self.other_item],
            },
            [self.visual, self.other_visual],
        )
        self.assertEqual(
            text,
            dedent(
                """\
                # Day 01 Learning Packet — Operating Systems Midterm

                ## First action
                - Start with `context_switch` and answer: Explain context-switch overhead.

                ## New blocks
                ### CPU Scheduling
                - Block type: mechanism
                - Importance: medium
                - Required learning behavior: explain, contrast, or reconstruct without notes before checking the source.
                - `context_switch` — Explain context-switch overhead.
                - `round_robin` — Explain round-robin fairness.

                ### Use Case Diagram
                - Block type: compare-contrast
                - Importance: high
                - Required learning behavior: explain, contrast, or reconstruct without notes before checking the source.
                - `include_vs_extend` — Explain include vs extend.

                ## Required visuals
                - `cpu-gantt-chart.png` for `round_robin`: Need the scheduling timeline diagram.
                - `uml-use-case-arrow.png` for `include_vs_extend`: Need the use-case arrow direction diagram.

                ## Done means
                - Each new item got at least one active attempt and is ready for same-day R0 recall.
                """
            ),
        )

    def test_learning_packet_renders_empty_state_without_crashing(self) -> None:
        text = build_learning_packet(self.course, 2, [], {}, [])
        self.assertEqual(
            text,
            dedent(
                """\
                # Day 02 Learning Packet — Operating Systems Midterm

                ## First action
                - No new blocks scheduled today.

                ## New blocks
                - None

                ## Required visuals
                - None

                ## Done means
                - Confirm there are no scheduled new blocks before ending the session.
                """
            ),
        )

    def test_recall_packet_sorts_queue_entries_and_visuals(self) -> None:
        early_entry = QueueEntry(
            item_id="context_switch",
            block_id="cpu_scheduling",
            status="R0",
            priority="high",
            last_result="partial",
            confidence="medium",
            next_review_day=1,
            next_review_date="2026-04-23",
            reason="needs faster retrieval",
        )
        late_entry = QueueEntry(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            status="R0",
            priority="urgent",
            last_result="wrong",
            confidence="high",
            next_review_day=2,
            next_review_date="2026-04-24",
            reason="comparison confusion",
        )
        text = build_recall_packet(
            self.course,
            1,
            [late_entry, early_entry],
            {
                "include_vs_extend": self.item,
                "context_switch": self.other_item,
            },
            [self.visual, self.other_visual],
        )
        self.assertLess(text.index("`context_switch`"), text.index("`include_vs_extend`"))
        self.assertLess(text.index("`cpu-gantt-chart.png`"), text.index("`uml-use-case-arrow.png`"))

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

    def test_final_pack_sorts_queue_entries_and_visuals(self) -> None:
        early_entry = QueueEntry(
            item_id="context_switch",
            block_id="cpu_scheduling",
            status="FINAL",
            priority="medium",
            last_result="partial",
            confidence="medium",
            next_review_day=8,
            next_review_date="2026-05-17",
            reason="timing terminology",
        )
        late_entry = QueueEntry(
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
            [late_entry, early_entry],
            {
                "include_vs_extend": self.item,
                "context_switch": self.other_item,
            },
            {
                "use_case_diagram": self.block,
                "cpu_scheduling": self.other_block,
            },
            [self.visual, self.other_visual],
        )
        self.assertLess(text.index("`context_switch`"), text.index("`include_vs_extend`"))
        self.assertLess(text.index("`cpu-gantt-chart.png`"), text.index("`uml-use-case-arrow.png`"))
        self.assertIn("Mistake-prevention checklist", text)

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
