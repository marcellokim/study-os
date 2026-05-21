# Daily Fresh Black-Box QA Design

Date: 2026-05-22

Status: Design approved; written spec awaiting user review. This document defines the next Study OS quality loop. It does not implement the changes.

## Goal

Daily evolution should stop relying only on the current conversation context or engine-internal assumptions. It should verify whether the next real Study OS learning action can improve exam answer accuracy when inspected by a fresh evaluator.

The core loop is:

```text
active course
  -> Study OS next action
  -> next packet
  -> fresh black-box two-phase QA
  -> 9-axis scorecard
  -> highest answer-rate blocker
  -> fix-priority for daily evolution
```

The goal is not to prove that Study OS generated a structurally valid packet. The goal is to test whether a learner who sees the packet fresh can produce a useful exam-style answer, self-grade it, and leave a signal that improves the next study action.

## Non-Goals

- Do not let fresh QA mutate canonical mastery, review queues, session history, or packet progress.
- Do not replace the user attempt and `close-session` path.
- Do not use random packet sampling as the daily default.
- Do not treat subagent answers as real learner performance.
- Do not block daily study for weak-but-usable packets unless the packet is not meaningfully learnable.
- Do not build course-specific one-offs that bypass the common Study OS exam-score loop.

## Daily Scope

Every daily evolution run should inspect all active courses. For each active course, Study OS chooses exactly one packet: the packet tied to the actual next learning action the user should take.

The daily default is:

```text
one active course -> one OS-recommended next packet -> one fresh black-box QA run
```

Risk-weighted rotation is useful for weekly or pre-merge benchmark suites, but it is not the daily default. Daily QA should verify the path the user is actually about to follow.

## Next Action Resolver

The next action resolver is responsible for selecting the packet under test. It reads current course state through supported Study OS surfaces, such as status, current day, generated packet files, and review queue state.

It must answer:

- Which course is active?
- What is the next Study OS-recommended learner action?
- Which packet should the user open next?
- Does that packet exist and open through the supported packet surface?

The resolver must not pick an arbitrary sample. If Study OS itself recommends the wrong next packet, that is a product-quality signal and should be visible in the daily QA result.

## Fresh Black-Box Protocol

Each selected packet is evaluated by a fresh subagent with no prior conversation-specific conclusions, implementation rationale, or expected outcome. The subagent receives only the material allowed for the current phase.

### Inspection Budget

The unit of daily selection is one packet per active course, but the subagent does not need to exhaustively answer every item when a packet is large.

The default item budget is:

```text
inspect all items when packet item count <= 5
inspect 5 items when packet item count > 5
```

When limiting to 5 items, the inspected set must include:

- the first item the packet asks the learner to handle
- at least one visual-dependent item when present
- at least one item marked urgent, high risk, wrong, partial, uncertain, or low-confidence when visible
- enough remaining items from packet order to preserve the user-flow perspective

This keeps daily QA bounded while still testing the actual next packet and the highest answer-rate risks inside it.

### Phase 1: Attempt

The subagent sees the packet as a learner would. It may inspect the prompt, answer surface, visible visuals, and packet context. It must not see answer keys, rubrics, source excerpts, or hidden grading material.

For each inspected item in the packet, Phase 1 records:

- whether the item is answerable from the packet
- a draft answer
- confidence from 1 to 5
- visible blockers
- whether the packet UI supports answer-first behavior

The subagent does not need to be correct. A wrong Phase 1 answer is useful when it reveals that the packet fails to support exam-style recall.

### Phase 2: Grading And Diagnosis

After Phase 1, the subagent may inspect the answer key, rubric, source refs, required visuals, and relevant source excerpts. It then grades the Phase 1 attempt and diagnoses the source of failure.

For each inspected item, Phase 2 records:

- `correct`, `partial`, `wrong`, or `uncertain`
- grading rationale
- whether the answer key and rubric support self-grading
- whether source refs and visuals support the item
- whether the item resembles a plausible exam task
- whether failure came from the packet, the source connection, the rubric, the visual asset, or normal learner difficulty

## Required Output Contract

Fresh QA should emit a structured result that daily evolution can consume. Markdown can be rendered for humans, but the machine-readable shape must be stable.

Required fields:

```text
course_slug
packet_type
day_index
next_action
phase1_attempts
phase2_grading
axis_scorecard
highest_answer_rate_blocker
fix_priority
gate
evidence
```

`axis_scorecard` uses the existing 9 improvement axes:

1. Exam transfer
2. Active recall
3. Grading quality
4. Risk-based priority
5. Visual/source connection
6. Session close and scheduling
7. Course-specific strategy
8. Outcome measurement
9. PDF visual intake

Each axis must be one of:

```text
OK | WEAK | BLOCKED | NOT_CHECKED
```

`gate` must be one of:

```text
pass | warn | block
```

## Gate Policy

Daily fresh QA is primarily a fix-priority engine, not a study blocker. Weak packets usually produce `gate=warn`, not `gate=block`.

Use `gate=block` only when the next packet is not meaningfully learnable:

- the packet does not exist or cannot be opened
- the prompt is course metadata or operating information rather than an exam task
- the learner cannot write an answer before checking support
- result, confidence, or blocker evidence cannot be recorded
- answer key or rubric is missing for a self-graded item
- required visual or source context is missing and the item cannot be solved without it
- packet attempts cannot become a close-session draft or next scheduling signal

Use `gate=warn` when the packet is usable but likely to reduce answer-rate improvement:

- exam transfer is weak
- answer key is too vague
- rubric misses common mistakes
- visuals are present but hard to interpret
- next packet ordering is plausible but not clearly risk-optimal
- course-specific strategy is generic

Use `gate=pass` only when the next packet supports answer-first execution, self-grading, confidence capture, and a plausible next scheduling signal.

## Daily Evolution Integration

Daily evolution should run this sequence:

1. Load active courses.
2. Resolve the next packet for each active course.
3. Dispatch one fresh black-box QA run per active course.
4. Convert each QA result into the 9-axis scorecard.
5. Select one `highest_answer_rate_blocker` per course.
6. Promote the largest cross-course issue into `global_fix_priority`.
7. Write a compact Korean daily report.

The daily report should include:

```text
Daily Fresh QA
- course_slug
- next_action
- packet_checked
- gate
- predicted_answer_rate_effect
- 9-axis scorecard
- highest_answer_rate_blocker
- fix_priority
- evidence
```

`predicted_answer_rate_effect` should be one of:

```text
positive | neutral | negative | unknown
```

## Failure Handling

Fresh QA failures and packet quality failures are different.

- `subagent_failed`: the evaluator failed to run. Mark relevant axes `NOT_CHECKED`, preserve the rest of daily evolution, and report the failure as infrastructure.
- `packet_blocked`: the packet cannot be opened or solved. Mark `gate=block`.
- `grading_blocked`: grading evidence is missing. Mark `gate=block` when self-grading is impossible, otherwise `gate=warn`.
- `learning_weak`: the packet is usable but not exam-strong. Mark `gate=warn`.
- `pass`: the packet supports the answer-rate loop. Mark `gate=pass`.

Subagent failure must not be recorded as learner failure. Synthetic or simulated attempts must be labeled as such.

## Testing Strategy

### Unit Tests

Unit tests should cover:

- next action resolver chooses the Study OS-recommended next packet
- result schema rejects missing required fields
- gate logic summarizes axis states and blockers consistently
- global fix-priority selection chooses the highest answer-rate blocker

### Fixture Simulation

Fixture tests should include:

- a good packet that returns `pass`
- a metadata-heavy packet that returns `warn` or `block`
- a packet with no answer key or rubric that returns `block`
- a visual-dependent packet with missing visual context that returns `block`
- a packet with no close-session path that returns `block`

### Runtime QA

Runtime QA should run against the active local courses:

- `basic-computer-programming-final`
- `software-engineering-midterm-testflight`

For each course, it should resolve the real next packet, run fresh black-box two-phase QA, and confirm that the daily report records course gate, 9-axis scorecard, evidence, and global fix-priority.

## Relationship To Existing Roadmap

This design extends the existing Exam-Score Spine. It strengthens daily evolution by making the QA source fresh and black-box, but it does not change the core product goal.

It supports the existing 9 improvement axes:

- It improves Exam transfer by testing whether prompts behave like exam tasks.
- It improves Active recall by verifying answer-first behavior.
- It improves Grading quality by testing answer key and rubric usefulness.
- It improves Risk-based priority by testing the OS-selected next packet.
- It improves Visual/source connection by checking visible assets and source refs.
- It improves Session close and scheduling by checking whether packet work can become close-session evidence.
- It improves Course-specific strategy by running every active course daily.
- It improves Outcome measurement by producing comparable daily QA signals.
- It improves PDF visual intake indirectly by exposing visual/source blockers in daily reports.

## Implementation Boundary

The next step after this design is a written implementation plan. That plan should focus on the smallest daily-evolution slice:

1. next action resolver
2. fresh QA result schema
3. gate and fix-priority summarizer
4. daily report integration
5. two-course runtime QA

Actual source ingestion improvements, weekly rotation benchmarks, and pre-merge benchmark suites should remain separate follow-up designs unless they are needed to make the daily next-packet QA loop work.
