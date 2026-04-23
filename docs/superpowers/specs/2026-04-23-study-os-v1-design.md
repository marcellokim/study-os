# Study OS v1 Design

## 1. Purpose

Study OS v1 is a filesystem-first learning operating system for exam preparation. It uses Codex as the conversational operating interface and a local workspace as the source of truth. The system manages long-horizon planning, day-by-day study execution, review scheduling, error tracking, and pre-exam final recall without relying on chat memory as persistent state.

The design goal is not to produce attractive summaries. The goal is to preserve operational state outside the conversation, reduce source-hunting overhead, enforce recall-oriented studying, and keep the system stable even if the LLM is inconsistent.

---

## 2. Core Design Decisions

### 2.1 Chosen Direction
- Filesystem-first, not Projects-first
- Codex-centered operating flow, but not Codex-trusting state mutation
- Multi-course workspace, with course-level independent operation
- Structured files only for canonical state
- Markdown outputs are derived artifacts and can be regenerated
- Database-free v1 using Markdown, YAML, JSON, and JSONL
- Manual source organization first; aggressive source extraction/automation is out of scope for v1

### 2.2 Core Principle
The system must not depend on Codex perfectly following a long prompt. Instead, it must constrain Codex behind explicit contracts and deterministic update logic.

### 2.3 Operational Philosophy
- Source files are preserved as originals
- State is explicit, structured, and inspectable
- Outputs are execution documents, not truth
- Study quality is judged by recallability, not familiarity
- Ambiguity is handled conservatively
- Visual-material-dependent items are gated until supporting images are available

---

## 3. System Identity and Scope

### 3.1 What the System Is
A multi-course study workspace where each course is an independent study engine that can:
- initialize from syllabus/slides/transcripts/images/notes
- decompose course scope into blocks and items
- generate learning and recall packets for a given study day
- track state transitions for item mastery
- record structured error events
- maintain a review queue
- generate a final recall pack before the exam

### 3.2 What the System Is Not
- a GUI app
- a database-backed service
- a general-purpose PDF visual understanding platform
- an automatic question-bank generator
- a cross-course optimizer in v1
- a chat-memory-driven workflow

---

## 4. Architecture Overview

The architecture is a **multi-course workspace with course-level independent state engines**.

### 4.1 Workspace Level
The workspace is a shared container for multiple courses. It may hold lightweight shared documentation and future metadata, but it is not where course mastery is computed.

### 4.2 Course Level
Each course is self-contained and includes:
- original sources
- canonical state files
- derived outputs
- manifests that connect source material to course structure

A course should be movable as a self-contained directory.

### 4.3 Codex Layer
Codex is the natural-language interface and orchestration layer. It:
- interprets user requests
- identifies intent and likely targets
- proposes state update requests
- explains outputs and next actions

Codex does **not** have arbitrary authority to mutate canonical state.

### 4.4 Deterministic Core Layer
A deterministic local core performs:
- schema validation
- state transitions
- review scheduling
- packet compilation
- canonical state writes

The same input request and current state must produce the same result.

---

## 5. Folder Structure

```text
study-os/
  workspace.md
  courses/
    <course-slug>/
      course.yaml
      sources/
        syllabus/
        slides/
        transcripts/
        images/
        notes/
      state/
        blocks.yaml
        items.yaml
        mastery.json
        review_queue.yaml
        error_log.jsonl
        session_history.jsonl
      manifests/
        source_manifest.yaml
        visual_requirements.yaml
      outputs/
        master_plan.md
        final_recall_pack.md
        daily/
          day_01_learning.md
          day_01_recall.md
```

### 5.1 Boundary Rules
- `sources/` = originals and source materials
- `state/` = canonical operational truth
- `manifests/` = mapping and gating metadata
- `outputs/` = regenerated execution documents

### 5.2 Canonical State
Canonical state lives only in structured state files. Derived Markdown must never be treated as the authoritative state source.

---

## 6. Core Domain Model

### 6.1 Block
A block is the operational grouping used for planning and day-packet composition.

Required attributes:
- `block_id`
- `block_name`
- `block_type`
- `importance`
- `difficulty`
- `exam_relevance`
- `needs_prereq`
- `needs_visuals`

Block types may include:
- concept-definition
- compare-contrast
- procedural-computation
- proof-derivation
- case-application
- diagram-interpretation
- written-answer
- memorization

### 6.2 Item
An item is the atomic recall/error/mastery tracking unit.

An item should:
- be recallable in one prompt or question
- represent a meaningful confusion boundary
- be small enough to evaluate, but not so small that the system becomes noisy

### 6.3 Mastery
`mastery.json` is the item-level snapshot of current learning state and cumulative outcomes.

### 6.4 Review Queue
`review_queue.yaml` is the action-oriented scheduling layer that decides what should be reviewed next and why.

### 6.5 Error Log
`error_log.jsonl` is the append-only event log of structured mistakes.

### 6.6 Session History
`session_history.jsonl` stores thin receipts of updates for traceability and debugging.

---

## 7. State Model and Transitions

### 7.1 State Ladder
```text
NEW → LEARNED → R0 → R1 → R2 → FINAL → MASTERED
```

This is not a one-way promotion ladder. It is a reversible state machine.

### 7.2 State Meaning
- `NEW`: not yet learned
- `LEARNED`: first-pass learning completed with at least one active learning action
- `R0`: same-day short recall needed
- `R1`: short-term review stage
- `R2`: medium-term review stage
- `FINAL`: pre-exam recall stage
- `MASTERED`: sufficiently stable by pre-exam operating standard

### 7.3 Promotion Rules
- `NEW → LEARNED`: only after first-pass learning plus at least one active action
- `LEARNED → R0`: automatic
- `R0 → R1`: same-day recall success with no core confusion
- `R1 → R2`: short-term review success
- `R2 → FINAL`: medium-term review success
- `FINAL → MASTERED`: successful pre-exam recall

### 7.4 Holding Rules
Promotion may be withheld when:
- confidence is low
- the answer is partial
- visual evidence is required but unavailable
- the user statement is too ambiguous to justify a stronger update

### 7.5 Regression Rules
Regression is allowed when any of the following occur:
- wrong answer
- low confidence on a supposedly known item
- missing condition or exception
- confusion of comparison boundary
- visual interpretation error
- skipped procedural step
- high-confidence wrong answer

High-risk regression signals:
- `C2` comparison confusion
- `C3` condition omission
- `C6` visual interpretation error
- `C8` overconfidence

These may cause stronger regression and closer re-review scheduling.

---

## 8. Review Scheduling Policy

Review timing is not a fixed interval table. It is policy-driven.

### 8.1 Inputs
The scheduler considers:
- days remaining until the exam
- block importance
- item difficulty
- exam relevance
- last result (`correct`, `wrong`, `partial`, `uncertain`)
- confidence
- repeated-error patterns
- error-code severity
- unresolved visual dependency

### 8.2 Outputs
For each queued item, the scheduler computes:
- `next_review_day` or `next_review_date`
- `priority`
- `reason`

### 8.3 Priority Escalation
Priority is increased for:
- high-confidence wrong answers
- repeated mistakes
- `C2`, `C3`, `C6`, `C8`
- high-importance blocks
- items still unstable near the exam date

---

## 9. Visual Gate Model

Visual dependence is treated as an operating gate, not as a memory-state subtype.

### 9.1 Trigger Conditions
The gate should activate when the critical learning target depends on:
- chart axes, legends, or trends
- diagrams or relationship maps
- image-based tables
- handwriting, highlighting, or symbolic arrows
- spatial math layout or matrix structure

### 9.2 Rules
- image-dependent items may be studied only within the range justified by available evidence
- missing required images prevent unjustified promotion
- required visuals must be surfaced in packet outputs
- visual requirements are tracked in manifests, not embedded into mastery states

---

## 10. Natural-Language Operation Model

The UX is fully conversational, but state updates are not free-form.

### 10.1 Supported High-Level Intents
- `INIT_COURSE`
- `START_DAY`
- `REQUEST_VISUALS`
- `CLOSE_SESSION`
- `START_FINAL_RECALL`
- read-only helpers such as `STATUS_CHECK`, `SHOW_QUEUE`, `SHOW_PLAN`

### 10.2 Processing Pipeline
1. intent detection
2. course resolution
3. evidence extraction
4. conservative interpretation
5. structured update request generation
6. deterministic core validation and application

### 10.3 Course Resolution Rules
Order of resolution:
1. explicitly named course
2. active course context
3. brief clarification only when no course can be reliably resolved

### 10.4 Conservative Interpretation Rules
- ambiguous signals should not cause strong promotion
- explicit mistakes should be recorded when item mapping is reliable
- visual uncertainty should suppress promotion on visual-dependent items
- missing confidence should default conservatively

---

## 11. Deterministic Core Contract

### 11.1 Core Responsibilities
The v1 deterministic core must provide:
- schema validation
- transition engine
- review scheduler
- packet builder

### 11.2 Write Boundary
Codex should not directly free-edit canonical files like `mastery.json` or `review_queue.yaml` as the normal update path.

Instead:
1. Codex interprets the conversation
2. Codex prepares an update request
3. the core validates it
4. the core mutates canonical state if valid
5. the core regenerates derived outputs

### 11.3 Update Request Shape
At minimum, a request may include:
- request type
- course id
- session date
- reviewed items
- item-level results
- confidence
- error code candidates
- notes
- ambiguity flags

### 11.4 Write Order
Canonical updates should occur in this order:
1. append error/event records
2. update mastery snapshot
3. recalculate review queue
4. regenerate outputs
5. write a session-history receipt

### 11.5 Result Types
The core should be able to return:
- `applied`
- `partially_applied`
- `rejected`
- `no_op`

---

## 12. Packet Generation Rules

Packets are user-facing execution documents. They are not truth.

### 12.1 Learning Packet
Purpose: first-pass learning execution.

Must include:
- today’s new blocks
- why those blocks matter today
- the first concrete study action
- target items and learning behaviors
- visual requirements
- conditions for counting the work as learned

The Learning Packet must not devolve into passive summary text.

### 12.2 Recall Packet
Purpose: same-day and scheduled recall execution.

Must prioritize:
- due `R0`
- overdue `R1` / `R2`
- high-risk mistakes
- repeated confusion patterns
- unstable exam-near items

It should be question-first and retrieval-first, not explanation-first.

### 12.3 Final Recall Pack
Purpose: pre-exam stabilization.

Must prioritize:
- important but unstable items
- repeated mistakes
- overconfidence mistakes
- comparison/condition/visual risk items
- answer skeletons and mistake-prevention checks

This document should suppress scope expansion and favor recall stability.

### 12.4 Daily Rule
“Start day” should always produce both:
- a Learning Packet
- a Recall Packet

The ratio can change, but the system should not allow a “new learning only” day that skips same-day recall.

---

## 13. Primary User Workflows

### 13.1 UC-1: Initialize Course
Input:
- course identity
- exam date or days remaining
- source materials present in the course folder

Output:
- course metadata
- block map
- item inventory draft
- visual requirement draft
- initial mastery and review queue
- master plan

### 13.2 UC-2: Start Day
Input:
- target course
- current review queue and mastery
- current day index or date

Output:
- learning packet
- recall packet
- required visuals
- first action to start immediately

### 13.3 UC-3: Close Session
Input:
- natural-language recap of correct/wrong/uncertain performance
- optional confidence cues
- optional notes about why something went wrong

Output:
- appended error log entries
- updated mastery
- updated review queue
- session receipt
- regenerated outputs if needed

### 13.4 UC-4: Start Final Recall
Input:
- target course
- current unstable items
- exam proximity

Output:
- final recall pack focused on recall, stabilization, and mistake prevention

---

## 14. File Schemas

### 14.1 `review_queue.yaml`
Example:
```yaml
- item_id: usecase-include-extend
  block_id: use_case_diagram
  status: R1
  priority: high
  last_result: wrong
  confidence: high
  next_review_day: 4
  reason: "overconfidence + direction confusion"
```

Required fields:
- `item_id`
- `block_id`
- `status`
- `priority`
- `last_result`
- `confidence`
- `next_review_day` or `next_review_date`
- `reason`

### 14.2 `error_log.jsonl`
Example:
```json
{"date":"2026-04-23","block_id":"use_case_diagram","item_id":"include_vs_extend","error_code":"C2","confidence":"high","note":"arrow direction reversed"}
```

Required fields:
- `date`
- `block_id`
- `item_id`
- `error_code`
- `confidence`
- `note`

### 14.3 `mastery.json`
Each item should store at least:
- current status
- last result
- consecutive success count
- last confidence
- last review date
- next review date/day

### 14.4 Error Codes
Required codes:
- `C1` concept omission
- `C2` comparison confusion
- `C3` condition omission
- `C4` skipped procedural step
- `C5` calculation mistake
- `C6` visual interpretation error
- `C7` written-expression imprecision
- `C8` overconfidence

---

## 15. Error Handling and Safety

The system prefers under-updating to corrupting state.

### 15.1 Failure Principles
- invalid input → reject
- ambiguous evidence → partial apply or no-op
- unresolved visual dependency → hold promotion
- item mismatch → avoid strong mutation
- stale outputs → rebuild from state

### 15.2 Common Failure Cases
- missing course resolution
- unresolvable item mapping
- malformed state file
- packet compilation failure despite valid state

Because source, state, and output are separated, failures should remain localized.

---

## 16. Verification Strategy

### 16.1 What Must Be Tested
- schema validity
- state transitions
- review scheduling
- packet compilation determinism

### 16.2 Test Examples
- `NEW -> LEARNED -> R0`
- `R1 + correct -> R2`
- `R2 + high-confidence wrong + C2 -> stronger regression`
- visual-required item with missing evidence does not promote
- same input request + same state yields same packet set

### 16.3 Human Review Points
Humans should still confirm:
- whether block/item decomposition matches exam reality
- whether visual dependencies are correctly identified
- whether final recall packs avoid scope expansion
- whether Codex interpretation has been too optimistic

---

## 17. v1 Scope and Explicit Non-Scope

### 17.1 In Scope
- multi-course workspace
- course-level independent operation
- structured state files
- initialization flow
- daily learning and recall packet generation
- session close updates
- final recall pack generation
- visual gating
- Codex front + deterministic core separation

### 17.2 Out of Scope
- automatic cross-course daily optimization
- database integration
- GUI/mobile app
- generalized PDF visual extraction
- full automatic question-bank generation
- dashboards and advanced analytics
- MCP-first architecture
- Obsidian integration
- parallel-agent orchestration as a v1 requirement

---

## 18. MVP Completion Criteria

Study OS v1 is complete when it can reliably do all of the following for at least one course:
1. initialize a course from prepared source folders
2. generate a daily learning packet and recall packet
3. record structured session outcomes
4. update mastery and review queue conservatively
5. enforce visual gating where appropriate
6. generate a final recall pack before the exam
7. reproduce the same results from the same state and same update request

---

## 19. Expected Design Artifacts

Minimum artifacts expected from this design:
- `requirements_to_architecture.md`
- `folder_structure.md`
- `file_schema.md`
- `state_transition_spec.md`
- `review_queue_spec.md`
- `mvp_execution_plan.md`

Optional helpful artifacts:
- packet templates
- example course folder
- sample update requests
- sample state-transition simulation

---

## 20. Final Summary

Study OS v1 is not a prompt trick. It is a filesystem-centered study operating system.

Its defining constraints are:
- canonical state lives in files, not in conversation
- Codex is the natural-language operating layer, not the unquestioned state authority
- a deterministic core protects the state model
- study packets are regenerated execution documents
- learning success is measured by recall stability and error correction, not by summary fluency

