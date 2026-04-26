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

    def test_learning_packet_renders_answer_support_when_item_metadata_exists(self) -> None:
        supported_item = Item(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            prompt="Explain include vs extend.",
            answer_mode="short-answer",
            difficulty="medium",
            exam_relevance="high",
            needs_visuals=True,
            learning_note="include는 공통 필수 하위 유스케이스를 재사용하고, extend는 조건부 확장 동작을 분리한다.",
            answer_key="include/extend의 실행 필수성, 의존 방향, 사용 조건을 모두 말해야 한다.",
            rubric="필수성 1점, 의존 방향 1점, 사용 조건 1점.",
            common_mistakes=["include를 실행 순서 화살표로 해석함", "extend를 항상 실행된다고 판단함"],
            source_refs=["slides/7 Larman Ch6.pdf", "transcripts/SE-0325전사본.txt"],
        )

        text = build_learning_packet(
            self.course,
            1,
            [self.block],
            {"use_case_diagram": [supported_item]},
            [self.visual],
        )

        self.assertIn("## 문항별 학습 카드", text)
        self.assertIn("핵심 개념: include는 공통 필수 하위 유스케이스", text)
        self.assertIn("정답 기준: include/extend의 실행 필수성", text)
        self.assertIn("채점 기준: 필수성 1점", text)
        self.assertIn("include를 실행 순서 화살표로 해석함", text)
        self.assertIn("slides/7 Larman Ch6.pdf", text)

    def test_recall_packet_renders_same_day_r0_checks_for_new_items(self) -> None:
        supported_item = Item(
            item_id="include_vs_extend",
            block_id="use_case_diagram",
            prompt="Explain include vs extend.",
            answer_mode="short-answer",
            difficulty="medium",
            exam_relevance="high",
            needs_visuals=True,
            answer_key="include는 필수 재사용, extend는 조건부 확장이라고 구분한다.",
            rubric="두 관계의 실행 조건과 의존 방향을 모두 포함한다.",
        )

        text = build_recall_packet(
            self.course,
            1,
            [],
            {"include_vs_extend": supported_item},
            [],
            new_items=[supported_item],
        )

        self.assertIn("## 당일 R0 회상", text)
        self.assertIn("먼저 답한 뒤 기준으로 채점", text)
        self.assertIn("정답 기준: include는 필수 재사용", text)

    def test_master_plan_mentions_blocks(self) -> None:
        text = build_master_plan(self.course, [self.block], [self.item])
        self.assertIn("학습 마스터 플랜", text)
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
                # Day 01 학습 패킷 — Operating Systems Midterm

                ## 첫 행동
                - 먼저 `context_switch`에 답하세요: Explain context-switch overhead.

                ## 신규 블록
                ### CPU Scheduling
                - 블록 유형: mechanism
                - 중요도: medium
                - 학습 방식: 노트를 보기 전에 설명, 비교, 재구성한다.
                - `context_switch` — Explain context-switch overhead.
                - `round_robin` — Explain round-robin fairness.

                ### Use Case Diagram
                - 블록 유형: compare-contrast
                - 중요도: high
                - 학습 방식: 노트를 보기 전에 설명, 비교, 재구성한다.
                - `include_vs_extend` — Explain include vs extend.

                ## 필요한 시각자료
                - `round_robin`: `cpu-gantt-chart.png` 필요 — Need the scheduling timeline diagram.
                - `include_vs_extend`: `uml-use-case-arrow.png` 필요 — Need the use-case arrow direction diagram.

                ## 완료 기준
                - 각 신규 문항을 최소 1회 능동 회상하고, 당일 R0 복습 준비 상태로 만든다.
                """
            ),
        )

    def test_learning_packet_renders_empty_state_without_crashing(self) -> None:
        text = build_learning_packet(self.course, 2, [], {}, [])
        self.assertEqual(
            text,
            dedent(
                """\
                # Day 02 학습 패킷 — Operating Systems Midterm

                ## 첫 행동
                - 오늘 새로 배울 블록이 없습니다.

                ## 신규 블록
                - 없음

                ## 필요한 시각자료
                - 없음

                ## 완료 기준
                - 세션을 끝내기 전에 예정된 신규 블록이 없는지 확인한다.
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
        self.assertIn("즉시 회상", text)
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
        self.assertIn("실수 방지 체크리스트", text)

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
        self.assertIn("실수 방지 체크리스트", text)
        self.assertIn("include_vs_extend", text)
