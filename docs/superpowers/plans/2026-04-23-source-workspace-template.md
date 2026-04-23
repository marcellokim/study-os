# Source Workspace Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the user-facing source-material folder obvious and safe for public-repo use.

**Architecture:** Keep runtime source materials in root-level `courses/<course_slug>/sources/`, but track only a non-runtime `workspace_template/` copy in Git. Add executable example request files and verify them through the CLI.

**Tech Stack:** Python standard library, `unittest`, Markdown, JSON.

---

### Task 1: Document source-material drop zones

**Files:**
- Modify: `README.md`
- Modify: `.gitignore`

- [ ] **Step 1: Update README with the source folder contract**

Add a section naming `courses/<course_slug>/sources/{syllabus,slides,transcripts,images,notes}` and explain that `init-course` creates these folders.

- [ ] **Step 2: Protect private runtime material from Git**

Add root-anchored ignore rules for `/courses/` and `/workspace.md` so real source materials and generated workspace indexes are not committed to the public repository.

### Task 2: Add tracked workspace template and examples

**Files:**
- Create: `workspace_template/courses/sample-course/sources/README.md`
- Create: `workspace_template/courses/sample-course/sources/syllabus/.gitkeep`
- Create: `workspace_template/courses/sample-course/sources/slides/.gitkeep`
- Create: `workspace_template/courses/sample-course/sources/transcripts/.gitkeep`
- Create: `workspace_template/courses/sample-course/sources/images/.gitkeep`
- Create: `workspace_template/courses/sample-course/sources/notes/.gitkeep`
- Create: `examples/sample_init_request.json`
- Create: `examples/sample_close_request.json`

- [ ] **Step 1: Add template source buckets**

Create the five source subdirectories with tracked `.gitkeep` files and a short README explaining what each bucket accepts.

- [ ] **Step 2: Add valid example requests**

Create sample init and close-session JSON payloads using `sample-course`, two blocks, two items, source manifest links, and one missing visual requirement.

### Task 3: Verify examples do not drift

**Files:**
- Create: `tests/integration/test_examples.py`

- [ ] **Step 1: Add example-flow integration test**

Write a test that copies `examples/sample_init_request.json` and `examples/sample_close_request.json` into a temporary workspace, runs `init-course`, `start-day`, `close-session`, and `start-final-recall`, then asserts the source folders and generated files exist.

- [ ] **Step 2: Run verification**

Run `bash scripts/check.sh` and expect all tests to pass.
