# Study OS Exam-Score Spine Design

Date: 2026-05-21

Status: Design approved; written spec awaiting user review. This document defines the vNext direction and the first implementation slice. It does not implement the changes.

## Goal

Study OS improvements must optimize for real exam answer accuracy. Packet validity, source ingestion depth, and UI polish matter only when they improve the user's ability to answer exam-like questions correctly.

The product spine is:

```text
source assets
  -> source insights
  -> exam-style question candidates
  -> learning / recall packet attempts
  -> grading signal
  -> risk queue
  -> next packet / close-session / daily evolution
```

The main design choice is `Exam-Score Spine`. The alternative `Source-Intelligence-First` approach is absorbed as the M1 source intelligence layer, not used as the top-level product direction.

## Non-Goals

- Do not make PDF/OCR quality the primary success metric.
- Do not auto-promote risky OCR output into answer keys.
- Do not overwrite canonical mastery directly from transient packet interaction.
- Do not prioritize visual polish unless it improves readability, active recall, feedback, prioritization, or exam transfer.
- Do not build course-specific one-offs that bypass the common Study OS loop.

## Core Architecture

### Source Assets

Source assets include PDFs, extracted text, page images, embedded images, tables, formulas, diagrams, screenshots, code images, and OCR output.

### Source Insights

Source insights are structured knowledge units that can plausibly affect exam answers. They should capture concepts, conditions, exceptions, comparisons, code patterns, diagram relationships, calculation procedures, and common traps.

### Question Candidates

Question candidates convert source insights into exam-style prompts. Course strategy profiles decide the dominant question shapes, for example code tracing for C programming or UML correction for software engineering.

### Packet Attempts

Packet attempts record what the user actually did in a learning or recall packet: draft answer, self-check result, confidence, blocker type, and timestamp.

### Grading Signal

The grading signal is:

```text
correct | partial | wrong | uncertain
confidence: 1-5
```

This signal is not a cosmetic UI state. It must affect risk ranking, close-session output, and future packet selection.

### Risk Queue

The risk queue ranks items by likelihood of losing exam points, not just by generic priority. It combines result, confidence, overdue state, exam likelihood, visual dependency, and course-specific importance.

### Daily Evolution

Daily evolution must report the highest answer-rate blocker and judge progress across the 9 improvement axes.

## 9 Improvement Axes

1. `Exam transfer`: packets should resemble the course's real exam tasks.
2. `Active recall`: packets should require the user to produce an answer, not just read.
3. `Grading quality`: result and confidence should be trustworthy enough to drive scheduling.
4. `Risk-based priority`: the next item should be the highest-value risk, not merely the next generated item.
5. `Visual/source connection`: questions should stay connected to source references and required visuals.
6. `Session close and scheduling`: a session should produce the next useful study action.
7. `Course-specific strategy`: common mechanics should support different exam styles per course.
8. `Outcome measurement`: improvement should be judged by retry results, risk resolution, and future mock scores.
9. `PDF visual intake`: PDF ingestion should include images, diagrams, formulas, tables, and OCR text inside visual regions.

Every proposed feature should answer two questions:

```text
Which axis does this improve?
Where does the signal remain in the exam-score loop?
```

If the improvement does not survive into packet attempts, grading signals, risk queues, close-session output, or outcome measurement, it should be deprioritized.

## Roadmap

### M0: Exam Loop Repair

M0 fixes the current packet loop so a user can open a packet, answer inside it, check the result, record confidence, and leave with the next weakness identified.

Scope:

- Add an in-packet answer-writing surface.
- Record `correct / partial / wrong / uncertain` plus confidence in the packet UI.
- Save and restore packet attempt state.
- Render available visual requirements as actual images when possible.
- Fall back to paths and descriptions when a visual cannot be rendered.
- Sort recall packets by real risk, with urgent and high-risk weak items above generic high-priority items.
- Add a useful empty state when a learning packet has no new items.
- Generate close-session draft output from wrong, partial, uncertain, and low-confidence answers.
- Keep packet progress separate from canonical mastery until an explicit close-session or commit path.
- Make daily evolution emit a 9-axis scorecard and one highest answer-rate blocker.

M0 success criteria:

- Basic Computer Programming and Software Engineering can both be QA-tested through the real user flow.
- The user can answer, self-check, set confidence, reload, and see the saved state.
- Software Engineering visual questions can display their required diagrams or clearly explain missing assets.
- Recall pages surface urgent/risky items first.
- Empty learning packets guide the user toward the next useful action.
- Close-session draft reflects today's wrong, partial, uncertain, and low-confidence answers.

### M1: Source Intelligence Intake

M1 implements the Source-Intelligence-First idea as a subordinate layer inside the exam-score spine.

Flow:

```text
PDF page
  -> text blocks
  -> image/table/formula/diagram/code regions
  -> OCR text
  -> classified source insight candidates
  -> confidence + risk label
  -> review-needed or auto-usable candidate
```

Auto-usable candidates may include clear text concepts, simple table text, and high-confidence low-risk OCR.

Review-needed candidates include formulas, UML/ERD/flowcharts, code snippets, complex tables, low-confidence OCR, or conflicting extracted text.

M1 success criteria:

- Visual or layout-encoded PDF content can become learning material.
- Risky visual/OCR output is not silently promoted into answer keys.
- Extracted assets can connect back to packet questions and source references.

### M2: Course Strategy And Measurement

M2 strengthens course-specific exam strategy and outcome tracking.

Course profile examples:

- Basic Computer Programming: code tracing, output prediction, arrays, pointers, fill-in code, error finding.
- Software Engineering: UML correction, concept comparison, process ordering, case application, operation contracts, sequence diagram interpretation.
- Data Science: formula meaning, calculation procedure, graph interpretation, model comparison, code/library usage judgment.

Measurement examples:

- Retry improvement after wrong or partial answers.
- Risk item resolution rate.
- Low-confidence-correct follow-up performance.
- Mock packet score trend.
- Per-course and per-question-type weakness trend.

M2 success criteria:

- Study OS can use different question templates and rubrics per course while preserving the common attempt/risk/measurement loop.
- Daily evolution can prioritize improvements based on outcome signals, not only static QA observations.

## M0 Detailed Design

### Attempt Data

Packet progress should store attempt data per item:

```yaml
item_id:
  draft_answer: "user-written answer"
  result: "correct | partial | wrong | uncertain"
  confidence: 1-5
  blocker_type: "concept | memory | application | visual | wording | careless | unknown"
  checked_at: "timestamp"
```

This state remains packet progress until close-session or an explicit commit path turns it into durable mastery/risk changes.

### Packet UI Flow

Each packet item should support this flow:

```text
question
source / visual context
answer textarea
self-check controls
confidence control
blocker type
answer key / rubric reveal
save state
```

Confidence should be selectable in the web UI. A 1-5 segmented control is preferred because it is fast, explicit, and easy to store.

### Visual Rendering

When a visual requirement is `status: available`, the packet renderer should display the actual image if the file exists and is browser-renderable. If the image cannot be rendered, the UI should show a clear fallback with the path and description.

This is a direct answer-rate issue for diagram-heavy questions such as UML correction.

### Risk Ranking

Recall ordering should prefer exam-loss risk:

```text
wrong > partial > uncertain > low confidence > overdue > high exam likelihood > visual dependent
```

The exact scoring can be additive, but the behavior must be testable: urgent/risky weak items should not be buried under generic high-priority items.

### Close Session

Close-session output should include:

- new weak points
- items to retry
- visual/source blockers
- low-confidence correct answers
- recommended next packet focus

`correct` with low confidence should remain a risk. `wrong` with `careless` should lean toward retry instead of concept re-teaching.

### Empty Learning State

When a learning packet has no new items, the page should not look broken or pointless. It should show:

- that no new learning items are available for the selected day
- the recommended next action, usually recall or close-session
- links or controls that take the user there

## Daily Evolution Contract

Daily evolution should produce:

```text
9-axis scorecard:
1. Exam transfer: OK / WEAK / BLOCKED / NOT_CHECKED
2. Active recall: OK / WEAK / BLOCKED / NOT_CHECKED
3. Grading quality: OK / WEAK / BLOCKED / NOT_CHECKED
4. Risk-based priority: OK / WEAK / BLOCKED / NOT_CHECKED
5. Visual/source connection: OK / WEAK / BLOCKED / NOT_CHECKED
6. Session close and scheduling: OK / WEAK / BLOCKED / NOT_CHECKED
7. Course-specific strategy: OK / WEAK / BLOCKED / NOT_CHECKED
8. Outcome measurement: OK / WEAK / BLOCKED / NOT_CHECKED
9. PDF visual intake: OK / WEAK / BLOCKED / NOT_CHECKED

highest answer-rate blocker:
- one concrete blocker

selected improvement:
- why this is the highest leverage for exam accuracy

evidence:
- course/page/user-flow checked
- command/browser QA result

next action:
- one implementation or QA step
```

Priority order:

```text
1. Problems that block the real answer-writing and checking flow.
2. Problems that lose grading, confidence, or risk data.
3. Problems that weaken exam-style transfer.
4. Missing visual/source connection.
5. Long-term OCR/source-intelligence gaps.
6. Pure UI polish.
```

UI polish may move upward when poor readability or layout directly reduces learning throughput or answer quality.

## QA Requirements

M0 QA must be performed through real user workflows:

- Basic Computer Programming Day 1 learning and recall: answer, check, confidence, save, reload.
- Software Engineering recall: visual-dependent question renders its required image or a clear fallback.
- Recall ordering: urgent/risky items appear before generic high-priority items.
- Empty learning packet: user sees the reason and the next action.
- Close-session draft: wrong, partial, uncertain, and low-confidence answers influence the next plan.

Browser QA should be used for packet UI behavior. CLI or test QA should be used for persistence, ranking, and close-session logic.

## Planning Boundary

The next step after this design is a written implementation plan for M0 only. M1 and M2 should stay in the roadmap until M0 proves that packet attempts, grading signals, risk ranking, and close-session output are working as one loop.
