# Study Workspace Separation Design

## Goal

Separate the Study OS engine repository from the runtime study workspace so a new Codex chat can reliably know whether it is developing Study OS itself or operating Study OS for a course.

The target behavior is simple: when the user starts a chat in the runtime workspace and says something like “software-engineering-midterm-testflight 분해해줘” or “오늘 study-os 시작,” Codex should act as a Study OS operator without the user re-explaining the engine path, workflow, or safety rules.

## Problem

The current `study-os` directory is doing two jobs:

1. Engine repository: `study_os/`, `tests/`, `scripts/`, `docs/`, and `workspace_template/` define and test the Study OS implementation.
2. Runtime workspace: `courses/software-engineering-midterm-testflight/` and `workspace.md` contain real course sources, generated state, manifests, and outputs.

This creates mode ambiguity. In a fresh chat, Codex can reasonably wonder whether it should edit engine code or operate a course. The project needs a stronger boundary than a long instruction paragraph inside the mixed repository.

## Approved approach

Use physical separation plus local operating instructions:

```text
/Users/ydmac/Documents/study-os
  Study OS engine repository

/Users/ydmac/Documents/study-workspace
  Study OS runtime workspace
```

The engine repo remains the place for source code, tests, docs, and reusable scripts. The runtime workspace becomes the place for private course materials, course state, generated packets, and Study OS operator instructions.

The first implementation phase includes:

1. Move runtime artifacts out of `study-os` into `study-workspace`.
2. Add a runtime-workspace `AGENTS.md` that defaults Codex to Study OS Operator mode.
3. Add a workspace-local `study-os-operator` skill so the user does not need to remember multi-step operating procedures.
4. Add a workspace wrapper command that runs the engine from `/Users/ydmac/Documents/study-os` against the runtime workspace.
5. Keep hooks out of phase one. Hooks can be added later only if `AGENTS.md` plus local skill are not enough.

## Directory layout

### Engine repository

```text
/Users/ydmac/Documents/study-os/
  .git/
  README.md
  docs/
  examples/
  scripts/
  study_os/
  tests/
  workspace_template/
```

The engine repository should not contain real runtime course materials. It may keep public templates and sample payloads.

### Runtime workspace

```text
/Users/ydmac/Documents/study-workspace/
  AGENTS.md
  study-os
  workspace.md
  .codex/
    skills/
      study-os-operator/
        SKILL.md
  courses/
    software-engineering-midterm-testflight/
      sources/
        syllabus/
        slides/
        transcripts/
        images/
        notes/
      init_request.json
      course.yaml
      manifests/
      state/
      outputs/
```

The runtime workspace may be a private git repository later, but it does not need to be one for phase one. Private PDFs, transcripts, notes, and generated state must not be committed accidentally.

## Operator mode contract

`study-workspace/AGENTS.md` should state that this directory is a runtime workspace, not the engine repo.

Default behavior in this workspace:

- Treat user requests about courses, sources, PDFs, transcripts, exams, study days, recall, and session closing as Study OS Operator tasks.
- Use the local `study-os-operator` skill for course operation.
- Read source files under `courses/<course_slug>/sources/`.
- Let Codex decompose sources into blocks, items, source manifest entries, and visual requirements.
- Write structured request files such as `init_request.json` and close-session requests.
- Apply state changes through the Study OS CLI.

Forbidden by default:

- Do not modify the Study OS engine implementation from the runtime workspace.
- Do not delete or rewrite original user PDFs, transcripts, notes, or images.
- Do not directly edit canonical engine-owned state files as the normal path: `mastery.json`, `review_queue.yaml`, `error_log.jsonl`, or `session_history.jsonl`.
- Do not treat Markdown outputs as canonical state.

## Local skill contract

The workspace-local skill should be named `study-os-operator`.

It should trigger when the user asks to:

- decompose course sources,
- initialize a course,
- start a study day,
- close a session,
- generate final recall,
- inspect course status,
- operate Study OS from the runtime workspace.

The skill body should stay concise and procedural. It should direct Codex to:

1. Detect the target course slug from the prompt or available `courses/` entries.
2. Run the wrapper with source validation when refreshing or initializing a course.
3. Inspect source manifest and source files before decomposition.
4. Generate or update `init_request.json` with exam-scope blocks/items, not a placeholder inventory, when doing real study setup.
5. Use Study OS CLI commands for state changes.
6. Report exact files changed, commands run, and next study action.

## Wrapper command

The runtime workspace should include a wrapper named `study-os`.

It should run the engine from the source repository against the runtime workspace, equivalent to:

```bash
PYTHONPATH=/Users/ydmac/Documents/study-os \
python3.13 -m study_os --workspace /Users/ydmac/Documents/study-workspace "$@"
```

This avoids requiring the user to remember `PYTHONPATH` or the engine path.

A future enhancement may allow the wrapper to auto-select Python 3.10+, matching `scripts/check.sh`, but phase one can use `python3.13` because that is available on this machine and already verified.

## Data flow

### Course setup

1. User puts files under `study-workspace/courses/<course_slug>/sources/`.
2. Codex runs the workspace-local preparation flow to index sources.
3. Codex reads PDF/TXT/notes as needed and replaces the placeholder source inventory with real blocks/items.
4. Codex runs `./study-os init-course --request-file courses/<course_slug>/init_request.json --validate-sources`.
5. The engine writes canonical state and derived outputs inside the runtime workspace.

### Daily operation

1. User asks to start or continue studying.
2. Codex uses `./study-os status --course <slug>` to inspect current state.
3. Codex runs `./study-os start-day ...` or prepares a close-session request depending on the task.
4. Codex never directly mutates engine-owned canonical state files.

## Error handling

- If the runtime workspace is missing, create only after explicit implementation approval.
- If the engine repo path is missing or invalid, stop with a clear path error and do not modify course state.
- If source validation fails, report the exact missing/invalid file and do not run `init-course`.
- If multiple courses exist and the user does not name one, infer only when one course is clearly active; otherwise ask one concise clarification.
- If a request sounds like engine development while in the runtime workspace, tell the user to switch to `/Users/ydmac/Documents/study-os` or explicitly confirm a builder task.

## Testing and verification

Phase-one verification should prove:

1. The engine repo no longer contains runtime `courses/` or root `workspace.md` after migration.
2. The runtime workspace contains the migrated `software-engineering-midterm-testflight` course.
3. The wrapper can run `status`, `init-course --validate-sources`, or an equivalent safe command against the runtime workspace.
4. The workspace `AGENTS.md` clearly defaults to Study OS Operator mode.
5. The local skill exists and documents the operator workflow.
6. Existing engine tests still pass with `bash scripts/check.sh`.

## Deferred hook strategy

Do not add hooks in phase one.

Hooks become worth considering only if fresh-chat behavior remains unreliable after physical separation, workspace `AGENTS.md`, and local skill. If added later, hooks should be workspace-scoped and conservative: they may suggest `study-os-operator` for course-operation prompts, but must not hijack explicit builder/code-edit requests.

## Success criteria

The design is successful when the user can start a new chat in `/Users/ydmac/Documents/study-workspace`, say “software-engineering-midterm-testflight 분해해줘,” and Codex reliably acts as a Study OS operator without needing the user to restate the engine path, source layout, or state mutation rules.
