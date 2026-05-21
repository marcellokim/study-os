# Study OS M0 Exam Loop Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Study OS packets work as an exam-score loop: users answer inside the packet, save a 1-5 confidence score and grading result, see required visuals, get risk-ranked recall, and generate a close-session draft without directly mutating mastery.

**Architecture:** Extend packet progress as execution-only state, then carry that state through packet models, HTML rendering, the localhost packet server, and close-session draft generation. Keep canonical mastery updates behind the existing `close-session` command, and keep visual-gated promotion logic based on missing visuals only.

**Tech Stack:** Python 3.10+ standard library (`dataclasses`, `datetime`, `html`, `http.server`, `json`, `mimetypes`, `pathlib`, `urllib.parse`, `unittest`), existing Study OS CLI and browser packet server.

---

## File Structure Map

- Modify: `study_os/core/packet_progress.py` — add `draft_answer`, `confidence_score` 1-5, `checked_at`, new blocker values, and compatibility with existing `confidence` strings.
- Modify: `tests/core/test_packet_progress.py` — cover the new attempt state and validation.
- Modify: `study_os/core/packet_models.py` — carry draft answers, confidence scores, visual status, and visual source paths.
- Modify: `study_os/core/packet_builder.py` — read new progress fields, add learning empty-state guidance, and use exam-risk recall ordering.
- Modify: `tests/core/test_packet_models.py` — cover draft/confidence propagation, empty learning state, and risk ordering.
- Modify: `study_os/core/packet_html.py` — render answer textareas, 1-5 confidence controls, image visuals, and close-session draft controls.
- Modify: `tests/core/test_packet_html.py` — cover answer UI, confidence UI, image rendering, and draft controls.
- Modify: `study_os/core/packet_server.py` — save draft/confidence attempts, serve workspace-local visual assets, and expose a close-session draft API.
- Modify: `tests/core/test_packet_server.py` — cover attempt persistence, asset serving, and draft endpoint behavior.
- Create: `study_os/core/risk_ranking.py` — shared queue-entry exam-risk sort key for HTML and Markdown packet output.
- Create: `tests/core/test_risk_ranking.py` — prove urgent/risky weak items sort before generic earlier due items.
- Modify: `study_os/core/packets.py` — use the shared risk sort and render visual status in Markdown fallback.
- Create: `study_os/core/close_session_draft.py` — build a read-only close-session request draft from packet progress.
- Create: `tests/core/test_close_session_draft.py` — cover confidence mapping, blocker/error-code mapping, and low-confidence correct risk.
- Modify: `study_os/core/engine.py` — include available visuals in packet outputs, preserve missing-only visual gating for mastery, add `build_close_session_draft`.
- Modify: `study_os/cli.py` — add `draft-close-session` command.
- Modify: `tests/core/test_engine_start_day.py` — update available-visual tests and empty-state expectations.
- Modify: `tests/core/test_engine_final_recall.py` — update available-visual final recall expectations.
- Modify: `tests/core/test_packets.py` — update recall/final sorting expectations.
- Modify: `tests/test_cli_smoke.py` — cover the new CLI command.
- Modify: `README.md` — document answer-writing, confidence scores, visual assets, and close-session draft workflow.

> **Constraint note:** the current worktree already contains unrelated modified and untracked Study OS files. Implementation must stage only files touched for the current task and must not revert existing user changes.

---

### Task 1: Extend Packet Attempt State

**Files:**
- Modify: `study_os/core/packet_progress.py`
- Modify: `tests/core/test_packet_progress.py`

- [ ] **Step 1: Write failing tests for draft answer, confidence score, checked timestamp, and blocker compatibility**

Add these tests to `tests/core/test_packet_progress.py`:

```python
    def test_set_packet_attempt_stores_draft_answer_confidence_score_and_checked_at(self) -> None:
        payload = {
            "learning:day:1": {
                "paging": {"checked": True},
            },
        }

        updated = set_packet_attempt(
            payload,
            packet_type="learning",
            day_index=1,
            item_id="paging",
            draft_answer="Paging maps virtual pages to physical frames.",
            result="partial",
            confidence_score=2,
            blocker_type="concept",
            checked_at="2026-05-21T09:30:00Z",
        )

        self.assertEqual(
            updated["learning:day:1"]["paging"],
            {
                "checked": True,
                "draft_answer": "Paging maps virtual pages to physical frames.",
                "result": "partial",
                "confidence": "low",
                "confidence_score": 2,
                "blocker_type": "concept",
                "checked_at": "2026-05-21T09:30:00Z",
            },
        )
        self.assertEqual(payload["learning:day:1"]["paging"], {"checked": True})

    def test_set_packet_attempt_rejects_invalid_confidence_score_and_draft_answer(self) -> None:
        with self.assertRaisesRegex(ValueError, "confidence_score"):
            set_packet_attempt(
                empty_packet_progress(),
                packet_type="learning",
                day_index=1,
                item_id="paging",
                confidence_score=0,
            )

        with self.assertRaisesRegex(ValueError, "confidence_score"):
            set_packet_attempt(
                empty_packet_progress(),
                packet_type="learning",
                day_index=1,
                item_id="paging",
                confidence_score=6,
            )

        with self.assertRaisesRegex(ValueError, "draft_answer"):
            set_packet_attempt(
                empty_packet_progress(),
                packet_type="learning",
                day_index=1,
                item_id="paging",
                draft_answer=["not", "text"],
            )

    def test_normalize_packet_progress_accepts_legacy_and_m0_blocker_types(self) -> None:
        payload = {
            "learning:day:1": {
                "legacy": {
                    "checked": False,
                    "confidence": "medium",
                    "blocker_type": "concept_connection_gap",
                },
                "m0": {
                    "checked": True,
                    "draft_answer": "answer",
                    "confidence_score": 5,
                    "blocker_type": "careless",
                    "checked_at": "2026-05-21T09:30:00Z",
                },
            }
        }

        normalized = normalize_packet_progress(payload)

        self.assertEqual(normalized["learning:day:1"]["legacy"]["confidence"], "medium")
        self.assertEqual(normalized["learning:day:1"]["legacy"]["blocker_type"], "concept_connection_gap")
        self.assertEqual(normalized["learning:day:1"]["m0"]["confidence"], "high")
        self.assertEqual(normalized["learning:day:1"]["m0"]["confidence_score"], 5)
        self.assertEqual(normalized["learning:day:1"]["m0"]["blocker_type"], "careless")
```

Also add `normalize_packet_progress` to the import list at the top of the file.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python3 -m unittest tests.core.test_packet_progress -v`

Expected: `ERROR` or `FAIL` because `set_packet_attempt()` does not accept `draft_answer`, `confidence_score`, or `checked_at`, and `normalize_packet_progress` does not preserve those fields yet.

- [ ] **Step 3: Implement confidence-score helpers and new validators**

In `study_os/core/packet_progress.py`, replace the type alias and blocker constants with:

```python
PacketProgressItem = dict[str, bool | int | str]
PacketProgressPayload = dict[str, dict[str, PacketProgressItem]]

_M0_BLOCKER_TYPE_VALUES = frozenset(
    {
        "concept",
        "memory",
        "application",
        "visual",
        "wording",
        "careless",
        "unknown",
    }
)
_LEGACY_BLOCKER_TYPE_VALUES = frozenset(
    {
        "prerequisite_gap",
        "concept_connection_gap",
        "math_gap",
        "code_gap",
        "visualization_gap",
        "terminology_gap",
        "source_confusion",
    }
)
_BLOCKER_TYPE_VALUES = _M0_BLOCKER_TYPE_VALUES | _LEGACY_BLOCKER_TYPE_VALUES
```

Add these helpers below `_validate_confidence`:

```python
def confidence_score_to_level(confidence_score: int | None) -> str:
    if confidence_score is None:
        return "unknown"
    _validate_confidence_score(confidence_score)
    if confidence_score <= 2:
        return "low"
    if confidence_score == 3:
        return "medium"
    return "high"


def _validate_confidence_score(confidence_score: int) -> None:
    if isinstance(confidence_score, bool) or not isinstance(confidence_score, int) or confidence_score < 1 or confidence_score > 5:
        raise ValueError("packet_progress confidence_score must be an integer from 1 to 5")


def _validate_draft_answer(draft_answer: str) -> None:
    if not isinstance(draft_answer, str):
        raise ValueError("packet_progress draft_answer must be a string")


def _validate_checked_at(checked_at: str) -> None:
    if not isinstance(checked_at, str) or not checked_at:
        raise ValueError("packet_progress checked_at must be a non-empty string")
```

Update `_validate_blocker_type` error text so it lists the M0 values first:

```python
        raise ValueError(
            "packet_progress blocker_type must be one of: "
            "application, careless, concept, memory, unknown, visual, wording "
            "or a legacy blocker value"
        )
```

- [ ] **Step 4: Preserve new fields during normalization**

Inside `normalize_packet_progress`, after `normalized_item: PacketProgressItem = {"checked": checked}`, insert:

```python
            draft_answer = progress.get("draft_answer")
            if draft_answer is not None:
                _validate_draft_answer(draft_answer)
                normalized_item["draft_answer"] = draft_answer

            confidence_score = progress.get("confidence_score")
            if confidence_score is not None:
                _validate_confidence_score(confidence_score)
                normalized_item["confidence_score"] = confidence_score
                normalized_item["confidence"] = confidence_score_to_level(confidence_score)

            checked_at = progress.get("checked_at")
            if checked_at is not None:
                _validate_checked_at(checked_at)
                normalized_item["checked_at"] = checked_at
```

Keep the existing `result`, legacy `confidence`, and `blocker_type` handling, but change the confidence block to avoid overwriting a derived score level:

```python
            confidence = progress.get("confidence")
            if confidence is not None and "confidence_score" not in normalized_item:
                if not isinstance(confidence, str):
                    raise ValueError("packet_progress confidence must be a string")
                _validate_confidence(confidence)
                normalized_item["confidence"] = confidence
```

- [ ] **Step 5: Extend `set_packet_attempt`**

Change the function signature in `study_os/core/packet_progress.py` to:

```python
def set_packet_attempt(
    payload: PacketProgressPayload,
    *,
    packet_type: str,
    day_index: int | None,
    item_id: str,
    draft_answer: str | None = None,
    result: str | None = None,
    confidence: str | None = None,
    confidence_score: int | None = None,
    blocker_type: str | None = None,
    checked_at: str | None = None,
) -> PacketProgressPayload:
```

Inside the function, before the existing `if result is not None` block, add:

```python
    if draft_answer is not None:
        _validate_draft_answer(draft_answer)
        next_item["draft_answer"] = draft_answer
    if checked_at is not None:
        _validate_checked_at(checked_at)
        next_item["checked_at"] = checked_at
```

Replace the confidence block with:

```python
    if confidence_score is not None:
        _validate_confidence_score(confidence_score)
        next_item["confidence_score"] = confidence_score
        next_item["confidence"] = confidence_score_to_level(confidence_score)
    elif confidence is not None:
        _validate_confidence(confidence)
        next_item["confidence"] = confidence
```

- [ ] **Step 6: Run the focused test and verify it passes**

Run: `python3 -m unittest tests.core.test_packet_progress -v`

Expected: `OK`

- [ ] **Step 7: Commit Task 1**

```bash
git add study_os/core/packet_progress.py tests/core/test_packet_progress.py
git commit -m "feat: extend packet attempt progress"
```

---

### Task 2: Add Shared Exam-Risk Ordering And Packet Model Fields

**Files:**
- Create: `study_os/core/risk_ranking.py`
- Create: `tests/core/test_risk_ranking.py`
- Modify: `study_os/core/packet_models.py`
- Modify: `study_os/core/packet_builder.py`
- Modify: `tests/core/test_packet_models.py`

- [ ] **Step 1: Write failing tests for risk order and packet model propagation**

Create `tests/core/test_risk_ranking.py`:

```python
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
```

Add this test to `tests/core/test_packet_models.py`:

```python
    def test_learning_packet_model_carries_draft_answer_confidence_score_and_empty_state(self) -> None:
        packet = build_learning_packet_model(
            self.course,
            day_index=3,
            blocks=[],
            items_by_block={},
            visuals=[],
            today="2026-05-21",
            progress_by_item={
                "paging": {
                    "checked": True,
                    "draft_answer": "My answer",
                    "confidence_score": 4,
                    "result": "correct",
                    "blocker_type": "careless",
                }
            },
        )

        self.assertEqual(packet.sections[1].entries, [])
        self.assertIn("복습 패킷", packet.sections[1].empty_state_text)
```

Add this test to `tests/core/test_packet_models.py`:

```python
    def test_recall_packet_model_uses_exam_risk_order(self) -> None:
        generic = QueueEntry(
            item_id="context_switch",
            block_id="cpu",
            status="R1",
            priority="high",
            reason="scheduled by state policy",
            next_review_date="2026-05-21",
            next_review_day=1,
            last_result="correct",
            confidence="medium",
        )
        urgent = QueueEntry(
            item_id="paging",
            block_id="memory",
            status="R1",
            priority="urgent",
            reason="overconfidence",
            next_review_date="2026-05-22",
            next_review_day=2,
            last_result="wrong",
            confidence="high",
        )

        packet = build_recall_packet_model(
            self.course,
            day_index=1,
            queue_entries=[generic, urgent],
            items_by_id={"paging": self.paging_item, "context_switch": self.context_switch_item},
            visuals=[],
            today="2026-05-21",
            progress_by_item={"paging": {"checked": True, "draft_answer": "answer", "confidence_score": 1}},
            new_items=[],
        )

        self.assertEqual([entry.item_id for entry in packet.sections[1].entries], ["paging", "context_switch"])
        self.assertEqual(packet.sections[1].entries[0].draft_answer, "answer")
        self.assertEqual(packet.sections[1].entries[0].confidence_score, 1)
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `python3 -m unittest tests.core.test_risk_ranking tests.core.test_packet_models -v`

Expected: `ERROR` because `study_os.core.risk_ranking` does not exist and packet models do not expose the new fields yet.

- [ ] **Step 3: Create shared risk-ranking helper**

Create `study_os/core/risk_ranking.py`:

```python
from __future__ import annotations

from study_os.core.models import QueueEntry


_FALLBACK_ORDER = 10**9
_PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
_RESULT_ORDER = {"wrong": 0, "partial": 1, "uncertain": 2, "correct": 3}
_CONFIDENCE_ORDER = {"low": 0, "unknown": 1, "medium": 2, "high": 3}


def queue_entry_exam_risk_key(entry: QueueEntry) -> tuple[int, int, int, bool, int, str, str]:
    return (
        _PRIORITY_ORDER.get(entry.priority, len(_PRIORITY_ORDER)),
        _RESULT_ORDER.get(entry.last_result, len(_RESULT_ORDER)),
        _CONFIDENCE_ORDER.get(entry.confidence, len(_CONFIDENCE_ORDER)),
        entry.next_review_day is None,
        entry.next_review_day if entry.next_review_day is not None else _FALLBACK_ORDER,
        entry.next_review_date or "",
        entry.item_id,
    )
```

- [ ] **Step 4: Extend packet dataclasses**

In `study_os/core/packet_models.py`, update `PacketVisual`:

```python
@dataclass(frozen=True)
class PacketVisual:
    item_id: str
    required_image: str
    description: str
    status: str = "missing"
```

Update `PacketEntry` by adding these fields after `checked`:

```python
    draft_answer: str | None = None
    result: str | None = None
    confidence: str | None = None
    confidence_score: int | None = None
    blocker_type: str | None = None
```

- [ ] **Step 5: Carry new progress fields and sort by risk**

In `study_os/core/packet_builder.py`, add:

```python
from study_os.core.risk_ranking import queue_entry_exam_risk_key
```

Update `_visuals_for`:

```python
def _visuals_for(visuals: list[VisualRequirement]) -> list[PacketVisual]:
    return [
        PacketVisual(
            item_id=visual.item_id,
            required_image=visual.required_image,
            description=visual.description,
            status=visual.status,
        )
        for visual in sorted(visuals, key=_visual_sort_key)
    ]
```

Inside `_entry_from_item`, read the new progress fields:

```python
        draft_answer = progress.get("draft_answer")
        result = progress.get("result")
        confidence = progress.get("confidence")
        confidence_score = progress.get("confidence_score")
        blocker_type = progress.get("blocker_type")
```

Pass them into `PacketEntry`:

```python
        draft_answer=draft_answer if isinstance(draft_answer, str) else None,
        result=result if isinstance(result, str) else None,
        confidence=confidence if isinstance(confidence, str) else None,
        confidence_score=confidence_score if isinstance(confidence_score, int) else None,
        blocker_type=blocker_type if isinstance(blocker_type, str) else None,
```

In `build_recall_packet_model` and `build_final_recall_packet_model`, replace `sorted(queue_entries, key=_queue_entry_sort_key)` with:

```python
sorted(queue_entries, key=queue_entry_exam_risk_key)
```

In `build_learning_packet_model`, set the `items` section to include empty-state guidance:

```python
            PacketSection(
                section_id="items",
                title="문항별 학습 카드",
                empty_state_text="오늘 새 학습 문항이 없습니다. 복습 패킷으로 이동해 위험 문항을 먼저 처리하세요." if not entries else None,
                entries=entries,
            ),
```

- [ ] **Step 6: Run focused tests and verify they pass**

Run: `python3 -m unittest tests.core.test_risk_ranking tests.core.test_packet_models -v`

Expected: `OK`

- [ ] **Step 7: Commit Task 2**

```bash
git add study_os/core/risk_ranking.py study_os/core/packet_models.py study_os/core/packet_builder.py tests/core/test_risk_ranking.py tests/core/test_packet_models.py
git commit -m "feat: rank packet recall by exam risk"
```

---

### Task 3: Render Answer Writing, 1-5 Confidence, And Visual Images

**Files:**
- Modify: `study_os/core/packet_html.py`
- Modify: `tests/core/test_packet_html.py`

- [ ] **Step 1: Write failing HTML rendering tests**

Add these tests to `tests/core/test_packet_html.py`:

```python
    def test_html_renders_answer_textarea_confidence_score_and_close_session_draft_button(self) -> None:
        packet = PacketPage(
            packet_type="learning",
            page_title="Day 01 학습 패킷",
            course_slug="operating-systems-midterm",
            course_name="Operating Systems Midterm",
            day_index=1,
            generated_date="2026-05-21",
            summary_text="summary",
            sections=[
                PacketSection(
                    section_id="items",
                    title="문항별 학습 카드",
                    entries=[
                        PacketEntry(
                            item_id="paging",
                            block_id="memory",
                            prompt="Explain paging.",
                            draft_answer="Maps pages to frames.",
                            result="partial",
                            confidence_score=2,
                            blocker_type="concept",
                        )
                    ],
                )
            ],
        )

        html = render_packet_html(packet, packet_links={"learning": "/packets/learning/day/1"})

        self.assertIn('<textarea data-action="draft-answer"', html)
        self.assertIn("Maps pages to frames.", html)
        self.assertIn('data-field="confidence_score"', html)
        self.assertIn('value="2" checked', html)
        self.assertIn('data-action="close-session-draft"', html)
        self.assertIn("loadCloseSessionDraft", html)

    def test_html_renders_available_visual_as_image_with_path_fallback(self) -> None:
        packet = PacketPage(
            packet_type="recall",
            page_title="Day 01 복습 패킷",
            course_slug="operating-systems-midterm",
            course_name="Operating Systems Midterm",
            day_index=1,
            generated_date="2026-05-21",
            summary_text="summary",
            sections=[
                PacketSection(
                    section_id="visuals",
                    title="시각자료 게이트",
                    visual_requirements=[
                        PacketVisual(
                            item_id="uml_fix",
                            required_image="courses/operating-systems-midterm/sources/images/uml.png",
                            description="UML correction diagram",
                            status="available",
                        )
                    ],
                )
            ],
        )

        html = render_packet_html(packet, packet_links={"recall": "/packets/recall/day/1"})

        self.assertIn('<figure class="packet-visual packet-visual-available"', html)
        self.assertIn('src="/assets/courses/operating-systems-midterm/sources/images/uml.png"', html)
        self.assertIn("UML correction diagram", html)
        self.assertIn("courses/operating-systems-midterm/sources/images/uml.png", html)
```

Add `PacketVisual` to the import list.

- [ ] **Step 2: Run the HTML tests and verify they fail**

Run: `python3 -m unittest tests.core.test_packet_html -v`

Expected: `FAIL` because the renderer has no textarea, no 1-5 score controls, no draft button, and no image visual rendering.

- [ ] **Step 3: Add HTML options and visual URL helper**

In `study_os/core/packet_html.py`, add:

```python
from urllib.parse import quote
```

Replace `_CONFIDENCE_OPTIONS` with:

```python
_CONFIDENCE_SCORE_OPTIONS = (
    (1, "1"),
    (2, "2"),
    (3, "3"),
    (4, "4"),
    (5, "5"),
)
```

Replace `_BLOCKER_OPTIONS` with:

```python
_BLOCKER_OPTIONS = (
    ("concept", "개념"),
    ("memory", "기억"),
    ("application", "응용"),
    ("visual", "시각자료"),
    ("wording", "표현"),
    ("careless", "실수"),
    ("unknown", "불명"),
)
```

Add:

```python
def _asset_url(relative_path: str) -> str:
    return "/assets/" + quote(relative_path.lstrip("/"), safe="/._-~")
```

- [ ] **Step 4: Add textarea and 1-5 confidence controls**

Add this helper near `_choice_group`:

```python
def _confidence_score_group(*, item_id: str, selected: int | None) -> str:
    choices = []
    for value, text in _CONFIDENCE_SCORE_OPTIONS:
        checked = " checked" if selected == value else ""
        choices.append(
            f"""
            <label class="packet-choice">
              <input type="radio" data-action="attempt" data-item-id="{escape(item_id)}"
                     data-field="confidence_score" name="confidence_score-{escape(item_id)}"
                     value="{value}"{checked}>
              <span>{escape(text)}</span>
            </label>
            """
        )
    return (
        '<div class="packet-choice-group"><span>자신감</span>'
        f'<div class="packet-choice-row">{"".join(choices)}</div></div>'
    )
```

Inside the per-entry loop, before `attempt_html`, add:

```python
            draft_answer_html = (
                '<label class="packet-answer-box">'
                '<span>내 답안</span>'
                f'<textarea data-action="draft-answer" data-item-id="{escape(entry.item_id)}" '
                'rows="5" placeholder="정답을 보기 전에 먼저 답을 작성하세요.">'
                f'{escape(entry.draft_answer or "")}'
                '</textarea>'
                '</label>'
            )
```

Replace the confidence `_choice_group(...)` call in `attempt_html` with:

```python
                + _confidence_score_group(
                    item_id=entry.item_id,
                    selected=entry.confidence_score,
                )
```

Render `draft_answer_html` before `attempt_html`:

```python
                    {draft_answer_html}
                    {attempt_html}
```

- [ ] **Step 5: Add visual figure rendering**

Replace the current `visual_html = "".join(...)` block with:

```python
        visual_html_parts: list[str] = []
        for visual in section.visual_requirements:
            image_html = ""
            visual_class = "packet-visual"
            if visual.status == "available":
                visual_class += " packet-visual-available"
                image_html = (
                    f'<img src="{escape(_asset_url(visual.required_image))}" '
                    f'alt="{escape(visual.description)}" loading="lazy">'
                )
            else:
                visual_class += " packet-visual-missing"
            visual_html_parts.append(
                f"""
                <figure class="{visual_class}" data-item-id="{escape(visual.item_id)}">
                  {image_html}
                  <figcaption>
                    <strong>{escape(visual.item_id)}</strong>
                    <span>{escape(visual.description)}</span>
                    <code>{escape(visual.required_image)}</code>
                  </figcaption>
                </figure>
                """
            )
        visuals_block = f'<div class="packet-visuals">{"".join(visual_html_parts)}</div>' if visual_html_parts else ""
```

Add CSS to `_style_block()`:

```css
      .packet-answer-box {
        display: grid;
        gap: 8px;
      }

      .packet-answer-box > span {
        color: var(--muted);
        font-size: 0.9rem;
        font-weight: 700;
      }

      .packet-answer-box textarea {
        width: 100%;
        min-height: 124px;
        resize: vertical;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 10px 12px;
        font: inherit;
        background: #ffffff;
      }

      .packet-draft-panel {
        display: grid;
        gap: 10px;
        margin-top: 12px;
        padding: 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fbfcfd;
      }

      .packet-draft-panel button {
        width: fit-content;
        min-height: 36px;
        border: 1px solid var(--accent);
        border-radius: 6px;
        background: var(--accent);
        color: #ffffff;
        font-weight: 700;
        padding: 6px 10px;
      }

      .packet-draft-panel pre {
        margin: 0;
        max-height: 320px;
        overflow: auto;
        white-space: pre-wrap;
      }

      .packet-visuals {
        display: grid;
        gap: 12px;
        margin: 12px 0 0;
      }

      .packet-visual {
        margin: 0;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #ffffff;
        overflow: hidden;
      }

      .packet-visual img {
        display: block;
        width: 100%;
        max-height: 520px;
        object-fit: contain;
        background: #f2f4f5;
      }

      .packet-visual figcaption {
        display: grid;
        gap: 4px;
        padding: 10px 12px;
      }
```

- [ ] **Step 6: Add JS save behavior for draft answers, 1-5 scores, and draft output**

Inside `applyEntryProgress`, add:

```javascript
        if (typeof progress.draft_answer === 'string') {
          const draftAnswer = container.querySelector('textarea[data-action="draft-answer"]');
          if (draftAnswer) {
            draftAnswer.value = progress.draft_answer;
          }
        }
        if (progress.confidence_score) {
          const confidenceInput = container.querySelector(`input[data-field="confidence_score"][value="${CSS.escape(String(progress.confidence_score))}"]`);
          if (confidenceInput) {
            confidenceInput.checked = true;
          }
        }
```

Inside the radio `change` handler, add selected score:

```javascript
          const selectedConfidenceScore = container.querySelector('input[data-field="confidence_score"]:checked');
```

And include it in `saveProgress`:

```javascript
              confidence_score: selectedConfidenceScore ? Number(selectedConfidenceScore.value) : undefined,
```

Add this textarea handler before `loadSavedProgress();`:

```javascript
      document.querySelectorAll('textarea[data-action="draft-answer"]').forEach((textarea) => {
        textarea.addEventListener('blur', async () => {
          const container = textarea.closest('.packet-entry');
          textarea.disabled = true;
          try {
            await saveProgress({
              action: 'attempt',
              item_id: textarea.dataset.itemId,
              draft_answer: textarea.value
            }, container);
          } finally {
            textarea.disabled = false;
          }
        });
      });
```

Add a draft panel after the header summary:

```python
        <div class="packet-draft-panel">
          <button type="button" data-action="close-session-draft">close-session draft</button>
          <pre data-close-session-draft aria-live="polite"></pre>
        </div>
```

Add JS before `loadSavedProgress();`:

```javascript
      async function loadCloseSessionDraft() {
        const output = document.querySelector('[data-close-session-draft]');
        if (output) {
          output.textContent = 'draft 생성 중';
        }
        const params = new URLSearchParams({
          packet_type: packetProgressContext.packet_type,
          session_date: {generated_date_json}
        });
        if (packetProgressContext.day_index !== null && packetProgressContext.day_index !== undefined) {
          params.set('day_index', String(packetProgressContext.day_index));
        }
        const response = await fetch(`/api/close-session-draft?${params.toString()}`);
        if (!response.ok) {
          if (output) {
            output.textContent = 'draft 생성 실패';
          }
          return;
        }
        const draft = await response.json();
        if (output) {
          output.textContent = JSON.stringify(draft, null, 2);
        }
      }

      document.querySelectorAll('[data-action="close-session-draft"]').forEach((button) => {
        button.addEventListener('click', loadCloseSessionDraft);
      });
```

Before the return string, add:

```python
    generated_date_json = _json_for_script(packet.generated_date or "")
```

- [ ] **Step 7: Run the HTML tests and verify they pass**

Run: `python3 -m unittest tests.core.test_packet_html -v`

Expected: `OK`

- [ ] **Step 8: Commit Task 3**

```bash
git add study_os/core/packet_html.py tests/core/test_packet_html.py
git commit -m "feat: render packet answer attempts"
```

---

### Task 4: Serve Visual Assets And Close-Session Draft API

**Files:**
- Create: `study_os/core/close_session_draft.py`
- Create: `tests/core/test_close_session_draft.py`
- Modify: `study_os/core/packet_server.py`
- Modify: `tests/core/test_packet_server.py`

- [ ] **Step 1: Write failing close-session draft tests**

Create `tests/core/test_close_session_draft.py`:

```python
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
                    "item_id": "uml_fix",
                    "phase": "review",
                    "result": "wrong",
                    "confidence": "high",
                    "error_code": "C6",
                    "note": "blocker=visual; answer=Wrong arrow direction.",
                },
                {
                    "item_id": "array_trace",
                    "phase": "review",
                    "result": "correct",
                    "confidence": "low",
                    "note": "blocker=careless; answer=I got the output but was unsure.",
                },
            ],
        )
        self.assertEqual(draft["next_focus"], ["array_trace", "uml_fix"])

    def test_ignores_items_without_result(self) -> None:
        draft = build_close_session_draft(
            course_slug="course",
            session_date="2026-05-21",
            packet_type="learning",
            day_index=1,
            packet_progress={"learning:day:1": {"array_trace": {"checked": True, "draft_answer": "answer"}}},
            items_by_id=self.items,
        )

        self.assertEqual(draft["reviewed_items"], [])
        self.assertEqual(draft["next_focus"], [])
```

- [ ] **Step 2: Write failing packet-server tests**

Add these tests to `tests/core/test_packet_server.py`:

```python
    def test_get_serves_workspace_asset_under_assets_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            image_path = workspace / "courses" / "operating-systems-midterm" / "sources" / "images" / "diagram.png"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"\x89PNG\r\n\x1a\nimage")

            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            CourseStore(paths).save_packet_progress({})

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request("GET", "/assets/courses/operating-systems-midterm/sources/images/diagram.png")
            response = connection.getresponse()
            body = response.read()
            content_type = response.getheader("Content-Type")
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 200)
            self.assertEqual(body, b"\x89PNG\r\n\x1a\nimage")
            self.assertEqual(content_type, "image/png")

    def test_get_assets_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            CourseStore(paths).save_packet_progress({})

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request("GET", "/assets/../secret.png")
            response = connection.getresponse()
            response.read()
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 404)

    def test_progress_post_persists_draft_answer_and_confidence_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            store = CourseStore(paths)
            store.save_packet_progress({"learning:day:1": {"paging": {"checked": True}}})

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request(
                "POST",
                "/api/progress",
                body=json.dumps(
                    {
                        "action": "attempt",
                        "packet_type": "learning",
                        "day_index": 1,
                        "item_id": "paging",
                        "draft_answer": "Paging maps pages.",
                        "confidence_score": 4,
                        "blocker_type": "careless",
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            saved = store.load_packet_progress()["learning:day:1"]["paging"]
            self.assertEqual(response.status, 200)
            self.assertTrue(payload["saved"])
            self.assertEqual(saved["draft_answer"], "Paging maps pages.")
            self.assertEqual(saved["confidence_score"], 4)
            self.assertEqual(saved["confidence"], "high")
            self.assertIn("checked_at", saved)

    def test_get_close_session_draft_returns_packet_progress_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            store = CourseStore(paths)
            store.save_items(
                [
                    {
                        "item_id": "paging",
                        "block_id": "memory",
                        "prompt": "Explain paging.",
                        "answer_mode": "short-answer",
                        "difficulty": "medium",
                        "exam_relevance": "high",
                        "needs_visuals": False,
                    }
                ]
            )
            store.save_packet_progress(
                {
                    "learning:day:1": {
                        "paging": {
                            "checked": True,
                            "draft_answer": "Maps pages.",
                            "result": "partial",
                            "confidence_score": 3,
                            "confidence": "medium",
                            "blocker_type": "concept",
                        }
                    }
                }
            )

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request(
                "GET",
                "/api/close-session-draft?packet_type=learning&day_index=1&session_date=2026-05-21",
            )
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 200)
            self.assertEqual(payload["reviewed_items"][0]["item_id"], "paging")
            self.assertEqual(payload["reviewed_items"][0]["phase"], "learning")
            self.assertEqual(payload["reviewed_items"][0]["result"], "partial")
```

- [ ] **Step 3: Run focused tests and verify they fail**

Run: `python3 -m unittest tests.core.test_close_session_draft tests.core.test_packet_server -v`

Expected: `ERROR` because `close_session_draft.py`, asset routes, and draft routes do not exist yet.

- [ ] **Step 4: Implement close-session draft builder**

Create `study_os/core/close_session_draft.py`:

```python
from __future__ import annotations

from typing import Any

from study_os.core.models import Item
from study_os.core.packet_progress import build_progress_key, confidence_score_to_level


_BLOCKER_ERROR_CODE = {
    "concept": "C1",
    "memory": "C1",
    "application": "C4",
    "visual": "C6",
    "wording": "C7",
    "careless": None,
    "unknown": None,
    "concept_connection_gap": "C2",
    "visualization_gap": "C6",
    "terminology_gap": "C7",
    "code_gap": "C4",
    "math_gap": "C5",
    "prerequisite_gap": "C1",
    "source_confusion": "C1",
}


def _phase_for_packet(packet_type: str) -> str:
    return "learning" if packet_type == "learning" else "review"


def _note_for(progress: dict[str, Any]) -> str:
    parts: list[str] = []
    blocker_type = progress.get("blocker_type")
    draft_answer = progress.get("draft_answer")
    if isinstance(blocker_type, str) and blocker_type:
        parts.append(f"blocker={blocker_type}")
    if isinstance(draft_answer, str) and draft_answer:
        parts.append(f"answer={draft_answer}")
    return "; ".join(parts)


def _confidence_for(progress: dict[str, Any]) -> str:
    confidence_score = progress.get("confidence_score")
    if isinstance(confidence_score, int):
        return confidence_score_to_level(confidence_score)
    confidence = progress.get("confidence")
    if isinstance(confidence, str):
        return confidence
    return "unknown"


def _is_focus_item(progress: dict[str, Any]) -> bool:
    result = progress.get("result")
    confidence = _confidence_for(progress)
    return result in {"wrong", "partial", "uncertain"} or (result == "correct" and confidence == "low")


def build_close_session_draft(
    *,
    course_slug: str,
    session_date: str,
    packet_type: str,
    day_index: int | None,
    packet_progress: dict[str, Any],
    items_by_id: dict[str, Item],
) -> dict[str, Any]:
    progress_key = build_progress_key(packet_type=packet_type, day_index=day_index)
    packet_items = packet_progress.get(progress_key, {})
    reviewed_items: list[dict[str, Any]] = []
    next_focus: list[str] = []

    for item_id in sorted(packet_items):
        if item_id not in items_by_id:
            continue
        progress = packet_items[item_id]
        if not isinstance(progress, dict):
            continue
        result = progress.get("result")
        if result not in {"correct", "partial", "wrong", "uncertain"}:
            continue

        reviewed: dict[str, Any] = {
            "item_id": item_id,
            "phase": _phase_for_packet(packet_type),
            "result": result,
            "confidence": _confidence_for(progress),
        }
        blocker_type = progress.get("blocker_type")
        error_code = _BLOCKER_ERROR_CODE.get(blocker_type) if isinstance(blocker_type, str) else None
        if result != "correct" and error_code is not None:
            reviewed["error_code"] = error_code
        note = _note_for(progress)
        if note:
            reviewed["note"] = note
        reviewed_items.append(reviewed)

        if _is_focus_item(progress):
            next_focus.append(item_id)

    draft: dict[str, Any] = {
        "course_slug": course_slug,
        "session_date": session_date,
        "reviewed_items": reviewed_items,
        "next_focus": next_focus,
    }
    if day_index is not None:
        draft["day_index"] = day_index
    return draft
```

- [ ] **Step 5: Implement asset serving and draft endpoint**

In `study_os/core/packet_server.py`, add imports:

```python
from datetime import datetime, timezone
import mimetypes
from urllib.parse import parse_qs, unquote, urlparse

from study_os.core.close_session_draft import build_close_session_draft
from study_os.core.models import Item
```

Add helper methods on `PacketServer`:

```python
    def _resolve_asset_file(self, path: str) -> Path | None:
        prefix = "/assets/"
        if not path.startswith(prefix):
            return None
        relative_path = unquote(path[len(prefix):])
        if not relative_path or Path(relative_path).is_absolute():
            return None
        resolved_workspace = self.workspace_root.resolve()
        resolved_path = (self.workspace_root / relative_path).resolve(strict=False)
        try:
            resolved_path.relative_to(resolved_workspace)
        except ValueError:
            return None
        if not resolved_path.exists() or not resolved_path.is_file():
            return None
        return resolved_path

    def _close_session_draft_from_query(self, query: str) -> dict[str, object]:
        params = parse_qs(query)
        packet_type = params.get("packet_type", [""])[0]
        session_date = params.get("session_date", [""])[0]
        day_text = params.get("day_index", [None])[0]
        day_index = int(day_text) if day_text not in {None, ""} else None
        items_by_id = {row["item_id"]: Item(**row) for row in self.store.load_items()}
        return build_close_session_draft(
            course_slug=self.course_slug,
            session_date=session_date,
            packet_type=packet_type,
            day_index=day_index,
            packet_progress=self.store.load_packet_progress(),
            items_by_id=items_by_id,
        )
```

Inside `Handler.do_GET`, after `parsed = urlparse(self.path)`, add:

```python
                if parsed.path == "/api/close-session-draft":
                    try:
                        self._write_json(parent._close_session_draft_from_query(parsed.query))
                    except (KeyError, TypeError, ValueError) as exc:
                        self._write_json({"error": str(exc)}, status=400)
                    return

                asset_file = parent._resolve_asset_file(parsed.path)
                if asset_file is not None:
                    self._write_file(asset_file)
                    return
                if parsed.path.startswith("/assets/"):
                    self.send_error(404)
                    return
```

Inside `Handler`, add:

```python
            def _write_file(self, path: Path, *, status: int = 200) -> None:
                encoded = path.read_bytes()
                content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
```

In `Handler.do_POST`, pass new attempt values:

```python
                            draft_answer=body.get("draft_answer"),
                            confidence_score=body.get("confidence_score"),
                            checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
```

- [ ] **Step 6: Run focused tests and verify they pass**

Run: `python3 -m unittest tests.core.test_close_session_draft tests.core.test_packet_server -v`

Expected: `OK`

- [ ] **Step 7: Commit Task 4**

```bash
git add study_os/core/close_session_draft.py study_os/core/packet_server.py tests/core/test_close_session_draft.py tests/core/test_packet_server.py
git commit -m "feat: draft close session from packet progress"
```

---

### Task 5: Include Available Visuals In Packets And Preserve Missing-Only Mastery Gating

**Files:**
- Modify: `study_os/core/engine.py`
- Modify: `study_os/core/packets.py`
- Modify: `tests/core/test_engine_start_day.py`
- Modify: `tests/core/test_engine_final_recall.py`
- Modify: `tests/core/test_packets.py`

- [ ] **Step 1: Update failing tests for available visuals and recall order**

In `tests/core/test_engine_start_day.py`, rename `test_start_day_excludes_available_visuals_from_user_packets` to:

```python
    def test_start_day_includes_available_visuals_in_user_packets(self) -> None:
```

Replace the final assertions with:

```python
            learning_text = paths.daily_dir.joinpath("day_01_learning.md").read_text(encoding="utf-8")
            recall_text = paths.daily_dir.joinpath("day_01_recall.md").read_text(encoding="utf-8")
            learning_html = paths.learning_packet_html_file(day_index=1).read_text(encoding="utf-8")
            recall_html = paths.recall_packet_html_file(day_index=1).read_text(encoding="utf-8")

            self.assertIn("uml-use-case-arrow.png", learning_text)
            self.assertIn("uml-use-case-arrow.png", recall_text)
            self.assertIn("status: available", learning_text)
            self.assertIn("status: available", recall_text)
            self.assertIn('src="/assets/uml-use-case-arrow.png"', learning_html)
            self.assertIn('src="/assets/uml-use-case-arrow.png"', recall_html)
```

In `tests/core/test_engine_final_recall.py`, rename `test_start_final_recall_excludes_available_visuals_from_pack` to:

```python
    def test_start_final_recall_includes_available_visuals_in_pack(self) -> None:
```

Replace the final assertions with:

```python
            pack_text = paths.final_recall_file.read_text(encoding="utf-8")
            html_text = paths.final_recall_html_file.read_text(encoding="utf-8")

            self.assertIn("## 필요한 시각자료", pack_text)
            self.assertIn("uml-use-case-arrow.png", pack_text)
            self.assertIn("status: available", pack_text)
            self.assertIn('src="/assets/uml-use-case-arrow.png"', html_text)
```

In `tests/core/test_packets.py`, update `test_recall_packet_sorts_queue_entries_and_visuals`:

```python
        self.assertLess(text.index("`include_vs_extend`"), text.index("`context_switch`"))
```

Update `test_final_pack_sorts_queue_entries_and_visuals`:

```python
        self.assertLess(text.index("`include_vs_extend`"), text.index("`context_switch`"))
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run: `python3 -m unittest tests.core.test_engine_start_day tests.core.test_engine_final_recall tests.core.test_packets -v`

Expected: `FAIL` because available visuals are still filtered out for packets and Markdown sorting still uses the old due-day-first key.

- [ ] **Step 3: Include all visuals in packet generation while keeping close-session gating missing-only**

In `study_os/core/engine.py`, keep `_pending_visual_requirements` unchanged. In `start_day`, replace:

```python
        visuals = _pending_visual_requirements(
            [VisualRequirement(**payload) for payload in store.load_visual_requirements()]
        )
```

with:

```python
        visuals = [VisualRequirement(**payload) for payload in store.load_visual_requirements()]
```

In `start_final_recall`, replace:

```python
        visuals = _pending_visual_requirements(
            [VisualRequirement(**row) for row in store.load_visual_requirements()]
        )
```

with:

```python
        visuals = [VisualRequirement(**row) for row in store.load_visual_requirements()]
```

Do not change `close_session`; it must continue to compute:

```python
        pending_visuals = _pending_visual_requirements(visuals)
```

- [ ] **Step 4: Use shared risk ordering and status-aware visual Markdown**

In `study_os/core/packets.py`, add:

```python
from study_os.core.risk_ranking import queue_entry_exam_risk_key
```

Replace both `sorted(queue_entries, key=_queue_entry_sort_key)` calls with:

```python
sorted(queue_entries, key=queue_entry_exam_risk_key)
```

In `build_learning_packet`, change the visual line to:

```python
            lines.append(f"- `{visual.item_id}`: `{visual.required_image}` 필요 — {visual.description} (status: {visual.status})")
```

In `build_recall_packet`, change the visual line to:

```python
            lines.append(f"- `{visual.item_id}`은/는 `{visual.required_image}` 확인 필요. status: {visual.status}")
```

In `build_final_recall_pack`, change the visual line to:

```python
            lines.append(f"- `{visual.item_id}`: `{visual.required_image}` (status: {visual.status})")
```

- [ ] **Step 5: Run focused tests and verify they pass**

Run: `python3 -m unittest tests.core.test_engine_start_day tests.core.test_engine_final_recall tests.core.test_packets -v`

Expected: `OK`

- [ ] **Step 6: Commit Task 5**

```bash
git add study_os/core/engine.py study_os/core/packets.py tests/core/test_engine_start_day.py tests/core/test_engine_final_recall.py tests/core/test_packets.py
git commit -m "feat: show available visuals in packets"
```

---

### Task 6: Add CLI Close-Session Draft Command And Documentation

**Files:**
- Modify: `study_os/core/engine.py`
- Modify: `study_os/cli.py`
- Modify: `tests/test_cli_smoke.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing CLI smoke test**

Add this test to `tests/test_cli_smoke.py`:

```python
    def test_draft_close_session_prints_reviewed_items_from_packet_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            init_request = workspace / "init.json"
            init_request.write_text(
                json.dumps(
                    {
                        "course": {
                            "course_slug": "sample-course",
                            "course_name": "Sample Course",
                            "exam_date": "2026-05-30",
                            "timezone": "Asia/Seoul",
                        },
                        "blocks": [
                            {
                                "block_id": "arrays",
                                "block_name": "Arrays",
                                "block_type": "code-tracing",
                                "importance": "high",
                                "difficulty": "medium",
                                "exam_relevance": "high",
                                "needs_prereq": False,
                                "needs_visuals": False,
                            }
                        ],
                        "items": [
                            {
                                "item_id": "array_trace",
                                "block_id": "arrays",
                                "prompt": "Trace the array output.",
                                "answer_mode": "short-answer",
                                "difficulty": "medium",
                                "exam_relevance": "high",
                                "needs_visuals": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            init_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "init-course",
                    "--request-file",
                    str(init_request),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            packet_progress = workspace / "courses" / "sample-course" / "state" / "packet_progress.yaml"
            packet_progress.write_text(
                json.dumps(
                    {
                        "learning:day:1": {
                            "array_trace": {
                                "checked": True,
                                "draft_answer": "prints 3",
                                "result": "partial",
                                "confidence_score": 2,
                                "confidence": "low",
                                "blocker_type": "concept",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "draft-close-session",
                    "--course",
                    "sample-course",
                    "--packet-type",
                    "learning",
                    "--day",
                    "1",
                    "--session-date",
                    "2026-05-21",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["reviewed_items"][0]["item_id"], "array_trace")
            self.assertEqual(payload["reviewed_items"][0]["confidence"], "low")
```

Ensure `json`, `subprocess`, `sys`, `tempfile`, and `Path` are imported in the file; reuse existing imports if present.

- [ ] **Step 2: Run the CLI test and verify it fails**

Run: `python3 -m unittest tests.test_cli_smoke.CliSmokeTest.test_draft_close_session_prints_reviewed_items_from_packet_progress -v`

Expected: `FAIL` because `draft-close-session` is not a recognized command.

- [ ] **Step 3: Add engine method**

In `study_os/core/engine.py`, import:

```python
from study_os.core.close_session_draft import build_close_session_draft
```

Add this method to `StudyEngine` before `status`:

```python
    def build_close_session_draft(
        self,
        course_slug: str,
        *,
        packet_type: str,
        day_index: int | None,
        session_date: str,
    ) -> dict[str, Any]:
        validate_course_slug_text(course_slug)
        validate_iso_date_text(session_date, "session_date")
        paths = build_course_paths(self.workspace_root, course_slug)
        if not paths.course_file.exists():
            raise ValidationError(f"unknown course_slug: {course_slug}")
        store = CourseStore(paths)
        items_by_id = {row["item_id"]: Item(**row) for row in store.load_items()}
        return build_close_session_draft(
            course_slug=course_slug,
            session_date=session_date,
            packet_type=packet_type,
            day_index=day_index,
            packet_progress=store.load_packet_progress(),
            items_by_id=items_by_id,
        )
```

- [ ] **Step 4: Add CLI parser and command**

In `study_os/cli.py`, add:

```python
    "draft-close-session": "Print a close-session request draft from saved packet progress.",
```

Add parser setup after `close_session_parser`:

```python
    draft_close_parser = subparsers.add_parser(
        "draft-close-session",
        help=COMMAND_HELP["draft-close-session"],
    )
    draft_close_parser.add_argument("--course", required=True)
    draft_close_parser.add_argument("--packet-type", required=True, choices=["learning", "recall", "final_recall"])
    draft_close_parser.add_argument("--day", type=int)
    draft_close_parser.add_argument("--session-date", required=True)
```

In `main`, after the `close-session` branch, add:

```python
        if parsed.command == "draft-close-session":
            draft = engine.build_close_session_draft(
                parsed.course,
                packet_type=parsed.packet_type,
                day_index=parsed.day,
                session_date=parsed.session_date,
            )
            print(json.dumps(draft, ensure_ascii=False, indent=2))
            return 0
```

- [ ] **Step 5: Update README workflow docs**

In `README.md`, update the feature bullets:

```markdown
- Saves per-item packet draft answers, self-check results, 1-5 confidence scores, and blocker types without changing mastery state.
- Serves available visual requirements as local packet images through the loopback packet server.
- Builds close-session request drafts from packet progress so mastery updates remain explicit.
```

Under `HTML Packet Workflow`, add:

````markdown
Inside a served packet:

1. Write the answer in the packet before revealing or checking the rubric.
2. Mark `correct`, `partial`, `wrong`, or `uncertain`.
3. Set confidence from 1 to 5.
4. Mark the blocker type if the answer was weak.
5. Use `close-session draft` to inspect the generated close-session request.

The same draft can be printed from the CLI:

```bash
python3 -m study_os --workspace "$tmp_workspace" draft-close-session \
  --course sample-course \
  --packet-type learning \
  --day 1 \
  --session-date 2026-04-23
```
````

- [ ] **Step 6: Run focused tests and verify they pass**

Run: `python3 -m unittest tests.test_cli_smoke.CliSmokeTest.test_draft_close_session_prints_reviewed_items_from_packet_progress -v`

Expected: `OK`

- [ ] **Step 7: Commit Task 6**

```bash
git add study_os/core/engine.py study_os/cli.py tests/test_cli_smoke.py README.md
git commit -m "feat: add close session draft command"
```

---

### Task 7: Full Verification And Real Workflow QA

**Files:**
- Modify only if verification exposes a concrete defect in files already touched by Tasks 1-6.

- [ ] **Step 1: Run the full engine test suite**

Run: `bash scripts/check.sh`

Expected: compileall succeeds and unittest discovery reports `OK`.

- [ ] **Step 2: Regenerate packets for both real courses**

Run:

```bash
./study-workspace/study-os start-day --course basic-computer-programming-final --day 1 --today 2026-05-21
./study-workspace/study-os start-day --course software-engineering-midterm-testflight --day 12 --today 2026-05-21
```

Expected: each command prints `applied` and includes generated HTML files under that course's `outputs/daily/`.

- [ ] **Step 3: Start packet server for Basic Computer Programming**

Run:

```bash
./study-workspace/study-os serve-packets --course basic-computer-programming-final --port 8765
```

Expected: server prints `http://127.0.0.1:8765` and keeps running.

- [ ] **Step 4: Browser QA Basic Computer Programming Day 1**

Open: `http://127.0.0.1:8765/packets/learning/day/1`

Check:

- each item has a visible answer textarea
- confidence has five choices
- selecting result/confidence/blocker saves and survives reload
- `close-session draft` shows JSON with `reviewed_items`
- no syllabus/exam-period metadata item appears as a study question

Stop the server after the check.

- [ ] **Step 5: Start packet server for Software Engineering**

Run:

```bash
./study-workspace/study-os serve-packets --course software-engineering-midterm-testflight --port 8766
```

Expected: server prints `http://127.0.0.1:8766` and keeps running.

- [ ] **Step 6: Browser QA Software Engineering visual recall**

Open: `http://127.0.0.1:8766/packets/recall/day/12`

Check:

- UML/diagram-dependent questions show actual available images or a clear path fallback
- urgent/risky weak items are above generic high-priority items
- answer/confidence/result state saves and survives reload
- close-session draft includes wrong/partial/uncertain and low-confidence correct items

Stop the server after the check.

- [ ] **Step 7: Verify no unintended runtime state was committed**

Run:

```bash
git status --short
```

Expected: only intentional engine/docs/test files are modified or committed. No files under `study-workspace/courses/` are staged.

- [ ] **Step 8: Commit verification fixes if needed**

If Tasks 1-6 commits are already clean and verification passes, do not create a no-op commit. If verification required fixes, commit them:

```bash
git add <fixed-engine-or-test-files>
git commit -m "fix: stabilize m0 exam loop repair"
```

---

## Self-Review Checklist For Implementers

- M0 scope only: no OCR extraction, no new database, no automatic mastery mutation from packet UI.
- Packet progress remains execution-only state.
- `close-session` remains the only path that writes mastery and review queue updates.
- Confidence is selectable as 1-5 in the web UI and stored as `confidence_score`.
- Existing `confidence` string remains derived for compatibility with close-session and scheduler logic.
- Available visuals render in packets; missing visuals still gate promotion.
- Recall ordering is based on exam-risk sort, not due-day-first sort.
- Close-session draft is read-only and inspectable before use.
- Full tests and two-course browser QA run before claiming completion.
