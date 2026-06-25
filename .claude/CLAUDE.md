# Claude Code: Vibe Coding Protocol

This document is the top-level guideline for collaborating with AI agents in this project. All work strictly follows the phases below.

> Code quality rules are owned by [.clauderules](../.clauderules); the macro lifecycle by
> [docs/pm-guide/lifecycle-standard.md](../docs/pm-guide/lifecycle-standard.md);
> and the recommendation/verification policy by [docs/pm-guide/recommendation_policy.md](../docs/pm-guide/recommendation_policy.md).

## 0. Core Principles

- **Separation of planning and implementation**: do not write code until the plan is approved.
- **Document-centric communication**: record every decision in project markdown files such as `research.md` and `plan.md`.
- **Keep ownership**: do not hand decision-making to the AI; the developer directs as the architect.

## 1. Phase-by-Phase Process

### Phase 1: Research (`research.md`)

- When starting new work, always analyze the relevant codebase first.
- **Instruction**: produce an in-depth analysis report, not a mere summary.
- **Prompt**: "Read this folder deeply and grasp every detail. When done, write a detailed report in `research.md`."

### Phase 2: Planning (`plan.md`)

- Based on the analysis, establish an implementation plan.
- **Instruction**: include the approach, the file paths to be modified, code snippets, and tradeoffs.
- **Functional specification (required)**: based on the functional-specification template adopted by the project, write a functional specification inside `plan.md`. (e.g. the SW/Web functional-spec templates registered under `docs/information/` or the charter. If no template exists, confirm with the developer.)
- **Memo loop**: the developer leaves comments (memos) in `plan.md`, and Claude reflects them and updates. Repeat until satisfied.
- **Prompt**: "Write a detailed implementation plan as `plan.md`. Referencing the functional-spec template, also write the functional specification. Do not modify any code yet."

### Phase 3: Iterative Implementation ({{SRC_ROOT}}/{{TESTS_ROOT}})

- Execute the approved plan incrementally per WBS unit, while running automated verification in parallel.
- **Instructions**:
  1. Write unit tests alongside every feature implementation.
  2. After completing each step, run the test script to check for regressions.
  3. Proceed to the next task only when tests pass.
- **Prompt**: "Implement everything. Check off the plan document each time you finish. Do not stop until every step is done, and keep running type checks."

### Phase 4: Delivery (staging/QA verification)

- Deploy the implementation to the staging environment and verify quality.
- **Instructions**:
  1. After confirming the full test suite passes, run the deployment script to the staging (Staging/QA) environment.
  2. Report the deployed results and the test report to the user.
  3. When QA verification is complete, request approval from the user.
- **Prompt**: "All tests are complete, so proceed with the staging deployment. After deployment, write the QA result report in `delivery_log.md` and request approval for the production deployment."

### Phase 5: Deployment (production deployment — approval required)

- Deploy the verified result to the production environment.
- **Instructions**:
  1. **Only when the user has given explicit approval (`[RELEASE APPROVED]`)** may the production (Production) deployment script be run.
  2. Until approval, the agent waits and does not access the production environment on its own.
  3. After deployment completes, record it in `deployment_log.md`. (Cite the verification number from `delivery_log.md` as a reference.)
- **Prompt**: "[RELEASE APPROVED] — proceed with the production deployment. When done, record it in deployment_log.md and reference the delivery_log.md verification number."

### Phase 6: Review & Assetization (knowledge assetization)

- After work completes, record failure/success patterns to perform knowledge assetization.
- **Instructions**:
  1. Through a retrospective, record the AI's misjudgments and effective prompts.
  2. Accumulate project-specific guidelines in `docs/retrospective/lessons_learned.md` as an asset.
- **Prompt**: "Record the issues that arose in this work and the approaches that were effective in lessons_learned.md."

## 2. Emergency Response Guide

- **Rollback**: if the implementation gets tangled, instead of patching incrementally, propose a rollback (git reset, etc.) to the developer, and after approval narrow the scope and retry.
- **UI/UX**: use screenshots for design issues that are hard to describe in words.
- **Constraint**: the developer explicitly draws the line on critical function signatures or library choices.

## 3. Harness Engineering Mode

This project proceeds in **harness engineering** style, where AI agents code the entire software except for safety boundaries.

- In Phase 3 (implementation), AI agents perform all of the coding.
- The user plays the architect/supervisor role (does not write code directly).
- **Safety boundary**: paths registered in `.harness.toml [safety_boundary].paths` (e.g. hardware adapters, emergency shutdown, third-party/undecided interfaces) are handled only as stub/mock until the user confirms them. The list is defined in that one place only ({{SAFETY_BOUNDARY_PATHS}}).
- **Task-level execution**: one M-task in plan.md = one execution unit.
- **Forward pipeline**: proceed sequentially in data-flow order. No parallel execution.

**Multi-engine model** — the harness runs across three engines; each has a fixed role:

| Engine | Role | Entry constraint file |
|--------|------|-----------------------|
| **Claude** | Orchestrator — plans, drives harness loop, runs verification, manages git | This file (CLAUDE.md) |
| **Codex** | Reviewer (default) + Implementer when delegated — Stage 1 RED / Stage 2 GREEN / Stage 5 FIX | `CODEX.md` + `.codex/agents/*.toml` |
| **Antigravity** | Documentation Writer — docs/wiki only, never code | `ANTIGRAVITY.md` |

**Every engine** must comply with the universal rules and write-scope contract in `AGENTS.md §12`.
When Claude delegates a task to Codex or Antigravity, the prompt must begin with the
"WRITE SCOPE IS CLOSED" header defined in `AGENTS.md §12.3`.

## 4. Task Execution Protocol

> **Engine assignment per stage**: `AGENTS.md §12.4` — Codex runs Stage 1/2/5 when delegated; Claude orchestrates Stage 3/4/6.
> Before delegating any stage to Codex or Antigravity, prepend the "WRITE SCOPE IS CLOSED" header (`AGENTS.md §12.3`).

```
1. Check the "next task" in progress.md
2. Read the task's DoD in plan.md
3. Write tests first — Codex (test-writer.toml) or Claude (RED)
4. Implement — Codex (impl-coder.toml) or Claude (GREEN) → refactor (IMPROVE)
5. Confirm pytest + mypy pass (Claude runs this)
6. Review — Claude + Codex in parallel (Stage 4)
7. git commit -m "<type>(<task-id>): <description> [HARNESS]"
8. Update progress.md (active → done, update next task)
```

> The single source for the stage→agent mapping of steps 3–8 is [.claude/commands/kit/harness-verify.md](commands/kit/harness-verify.md).
> The 6-stage thresholds and permission matrix are in [docs/_harness/quality-gates.md](../docs/_harness/quality-gates.md).
> The task-id format is `.harness.toml [task_id].regex` (multi-segment allowed).

## 5. Session Recovery Protocol

When resuming after an interruption, always check state in the following order:

```
1. cat docs/ai-workflow/progress.md → confirm current task/status
2. git log --oneline --grep=HARNESS -5 → last checkpoint
3. git status → check uncommitted changes
4. pytest tests/ -x --tb=short → test status
5. Resume work based on the above information
```

### 5.1 "context check" command — fast reorientation via the Foam knowledge base

When the user says **"context check"**, you **must** read the Foam entry points below and then **summarize the current context in 3–5 concise lines** before proceeding:

```
1. docs/index.md            → knowledge-base entry point (MOC, domain router)
2. docs/_recent.md          → most-recent first (start from recent work / high-confidence docs)
3. docs/_authority.md       → single-authority documents (current basis)
4. docs/_field_cascade.md   → field → the documents that use it (for spec/field work)
5. docs/ai-workflow/progress.md + git status → current active task / uncommitted changes
```

Summary format: **[current location (Phase/task)] · [what is the basis (authority)] · [next step]**.
If the catalog is stale, regenerate with `python scripts/foam_catalog.py` / `python scripts/field_cascade.py` before reading.

## 6. Error Recovery Rules

- **Test failure**: fix the implementation, do not change the tests.
- **Build failure**: use the build-error-resolver agent.
- **3 consecutive failures**: escalate to the user.
- **Safety-boundary-related errors**: check `.harness.toml [safety_boundary]`, resolve at the stub level, and report actual hardware/external-interface issues to the user.

## 7. Verification Gates

- **On M-task completion**: `pytest tests/unit/test_{module}.py -v --cov={{SRC_ROOT_DOTTED}}.{module} --cov-fail-under={{COVERAGE_THRESHOLD}}`
  - Note: specify the `--cov` target as a **dotted module path** (not a filesystem path — a file path makes coverage count a false 0%).
- **On Milestone completion**: `pytest tests/ -v --cov={{SRC_ROOT_DOTTED}} --cov-fail-under={{COVERAGE_THRESHOLD}} && mypy {{SRC_ROOT}}`
- **Integration-test stage**: run the full integration test suite.
- **Final stage**: run the E2E tests.

> **Ring naming**: the "integration-test"/"E2E" stages above are the kit's test-pyramid levels. The compositional **Unit/Module/Integration rings** ([docs/_harness/compositional-verification.md](../docs/_harness/compositional-verification.md)) are a *separate axis* — see its §0 terminology bridge.

> The actual command strings are single-sourced in `.harness.toml [language]` (`test_cmd`/`coverage_cmd`/`type_cmd`).

## 8. Single-Authority Specifications (enforced rule)

For certain domain areas, this project operates a **single-authority specification**. When working in such an area, always reference only the latest version of the specification, never routing around it via scattered material.

> The table below is an **empty registry**. When the project freezes a contract such as a data definition, output sink, or identifier/unit (Gate P),
> register that authority document here one row at a time. Once registered,
> `python scripts/foam_catalog.py` reflects it automatically in `docs/_authority.md`.

| Domain | Single-Authority Specification | Start Version |
|:---|:---|:---:|
| {{DOMAIN_NAME}} | [`docs/engineering/{{SPEC_FILE}}.md`](../docs/engineering/{{SPEC_FILE}}.md) | v1.0 ({{YYYY-MM-DD}}) |

**Enforced rules**:
1. When working in that domain = reference only the latest § of that spec.
2. When the spec conflicts with scattered material (analysis reports, vendor-manual analyses, decision trackers, etc.) = the spec always wins.
3. When a definition needs to change = edit it within the spec, incrementing the version in the Changelog (no routing around it via other material).
4. When you find an item missing from the spec = decide, then integrate it into the spec + increment the version.
5. Editing other material directly without reflecting it in the spec = forbidden (two systems coexisting = a stopgap, raising future correction cost).

> A *value* defined by a single-authority spec is not a choice — it is to be complied with. If the code differs from the spec, the code is wrong.
> For the detailed recommendation discipline, see [docs/pm-guide/recommendation_policy.md](../docs/pm-guide/recommendation_policy.md) §2.

> Document **format** conventions (filenames, meta blocks, wikilinks, MOC, trust model) are owned by [`docs/_knowledge-architecture.md`](../docs/_knowledge-architecture.md) — **content authority is this §8, format is orthogonally separated to that file**.
