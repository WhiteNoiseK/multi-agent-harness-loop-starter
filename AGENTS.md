# {{PROJECT_NAME}} — Agent Instructions

> **Project**: {{PROJECT_DESCRIPTION}}
> **Mode**: Harness engineering (AI agents code all SW except the safety boundaries)
> **Protocol**: VHCP 6-Phase × 6-stage quality gate

This document is the top-level instruction for every AI agent — including the Antigravity IDE and Claude Code — collaborating on this project. **Before starting any work, read this document, identify your current Phase and task, and only then proceed.**

---

## 1. Single Entry Points

| Document | Role |
|------|------|
| [AGENTS.md](AGENTS.md) (this file) | **Top-level instruction** — every agent starts here |
| [.clauderules](.clauderules) | 6-Phase compliance rules + canonical language-agnostic code quality |
| [.claude/CLAUDE.md](.claude/CLAUDE.md) | The detailed VHCP protocol for Claude Code (per-Phase prompts) |
| [.claude/commands/kit/harness-verify.md](.claude/commands/kit/harness-verify.md) | **Single source for the stage→agent mapping** (Stage 3→6 orchestration) |
| [docs/pm-guide/lifecycle-standard.md](docs/pm-guide/lifecycle-standard.md) | **Macro lifecycle (8 stages)** — including Gate P (3-contract freeze) |
| [docs/_harness/quality-gates.md](docs/_harness/quality-gates.md) | **The 6-stage quality-gate engine** (thresholds·permission matrix·JSON schema) |
| [docs/index.md](docs/index.md) | **Knowledge-base entry point (MOC)** — most-recent/authority catalogs. Format conventions: [docs/_knowledge-architecture.md](docs/_knowledge-architecture.md) |
| [docs/ai-workflow/codex_claude_review_protocol.md](docs/ai-workflow/codex_claude_review_protocol.md) | **Multi-agent collaboration** — Single Writer / Independent Reviewer (e.g. Claude ↔ Codex), R0–R4 |

> **📌 Document authority declaration (mandatory on creation).** When creating any project-knowledge or
> system-rule document, put the authority tag on the line **right below the H1 title**: `#authority/[type]/[level]`.
> The naming **differs by category** — do not mix them up:
> - **Project Knowledge (Domain)** = content/spec/decision/research → `#authority/domain/{supreme | single | derived | deprecated}` (지식: 최고/단일/**파생(비권위)**/폐기)
> - **System/Format Rules (System)** = how-to-write/convention/process/template/rule → `#authority/system/{absolute | active | inactive | deprecated}` (규칙: 절대/활성/비활성/폐기)
>
> ⚠️ Rules have **no "derived"** (a rule without authority is not a rule); only Knowledge has `derived`.
> Full taxonomy and metadata-block format: [docs/_knowledge-architecture.md §2](docs/_knowledge-architecture.md).

---

## 2. Required Pre-action Hook When an Agent Resumes

When the user requests "continue," "next task," "resume," **"context check"**, etc., **always auto-run the following sequence in order**:

```
1. Read docs/index.md · docs/_recent.md · docs/_authority.md · docs/_field_cascade.md → Foam knowledge base (MOC·most-recent·authority·field dependency) ※ the core of "context check"
2. Read docs/ai-workflow/progress.md       → confirm the current active task
3. Read docs/ai-workflow/plan.md (the relevant M-task section)  → confirm the DoD
4. Read docs/ai-workflow/implementation_log.md (the last 2–3 entries) → restore the immediately preceding state
5. git log --oneline --grep=HARNESS -5     → the last HARNESS checkpoint
6. git status                              → check for uncommitted changes
7. Summarize and resume from the above (proceed automatically without user confirmation)
```

---

## 3. VHCP 6-Phase × Agent/Workflow Mapping

> For the mapping to the macro lifecycle (8 stages, including Research/Feasibility), see [docs/pm-guide/lifecycle-standard.md](docs/pm-guide/lifecycle-standard.md).

| Phase | VHCP Deliverable | Supporting Agent | Workflow (command) |
|-------|-----------|-----------|---------------------|
| **Phase 1: Research** | `docs/ai-workflow/research.md` | `planner`, `architect` | `/plan` |
| **Phase 2: Planning** | `docs/ai-workflow/plan.md` (WBS + DoD) | `planner`, `architect` | `/plan` |
| **Phase 3: Implementation** | `{{SRC_ROOT}}/`, `{{TESTS_ROOT}}/`, `implementation_log.md` | `test-writer`, `impl-coder`, `code-reviewer`, `security-reviewer`, `refactor-fixer`, `score-auditor`, `build-error-resolver` | `/kit:harness-verify`, `/tdd`, `/code-review`, `/build-fix` |
| **Phase 4: Delivery** | `delivery_log.md` (staging/QA) | `e2e-runner`, `security-reviewer` | `/e2e`, `/test-coverage`, `/quality-gate` |
| **Phase 5: Deployment** | `deployment_log.md` (deploy after approval) | — | `/verify`, `/checkpoint` |
| **Phase 6: Retrospective** | `docs/retrospective/lessons_learned.md` | `doc-updater` | `/learn`, `/evolve` |

> **Phase 5 production deployment runs only after explicit `[RELEASE APPROVED]` approval.**

---

## 4. Harness Task Execution Protocol (Phase 3 iteration loop)

```
[Per-task execution chain]

1. test-writer agent → write tests from the Phase 2 DoD (RED)
2. impl-coder agent → minimal implementation (GREEN) → refactor (IMPROVE)
3. Run the verification gate (/kit:harness-verify):
   - Single task: pytest tests/unit/test_{module}.py --cov={{SRC_ROOT_DOTTED}}.{module} --cov-fail-under={{COVERAGE_THRESHOLD}}
   - Milestone complete: pytest tests/ --cov={{SRC_ROOT_DOTTED}} --cov-fail-under={{COVERAGE_THRESHOLD}} && mypy {{SRC_ROOT}}
     ※ the --cov target is a dotted module path (not a filesystem path)
4. code-reviewer + security-reviewer in parallel → resolve CRITICAL/HIGH issues (Stage 4)
5. git commit -m "<type>(<task-id>): <description> [HARNESS]"
6. Update docs/ai-workflow/progress.md (active→done + next task)
7. Proceed to the next task

[Error recovery]
- 3 consecutive test failures    → escalate to the user
- Build failure                  → bring in the build-error-resolver agent
- Beyond the safety-boundary stub scope → ask the user for confirmation (never proceed unilaterally)
```

> The responsible agent and permission matrix for each step are single-sourced in [.claude/commands/kit/harness-verify.md](.claude/commands/kit/harness-verify.md) and [docs/_harness/quality-gates.md](docs/_harness/quality-gates.md). This section only summarizes the flow.

---

## 5. Safety Boundary (Hard Boundary)

> The table below is an **empty registry**. Register paths that must not be auto-modified — hardware adapters, emergency shutdown,
> outsourced/undecided interfaces, etc. — in `.harness.toml [safety_boundary].paths`, and mirror each one as a row here.
> The single source for the list is `.harness.toml` alone — do not duplicate or re-describe it here.

| File/path | Status | Rule |
|------|------|------|
| `{{SAFETY_BOUNDARY_PATH}}` | **STUB ONLY** | Implement the real interface only after the user confirms. Until then, mock/stub |

**Agents do not unilaterally modify safety-boundary areas.** Always substitute a mock/stub, and if a change is needed, explicitly ask the user for confirmation.

---

## 6. Open CONFLICT Items (review before any work)

> Register here the conflicting/unresolved items that must be decided before starting (linked to Gate P freeze targets).

| ID | Description | When a decision is needed |
|----|------|--------------|
| {{CONFLICT_ID}} | {{description}} | Before starting {{task}} |

---

## 7. Commit Convention ([HARNESS] tag required)

```
Format: <type>(<task-id>): <description> [HARNESS]

Examples:
  feat(M1-05): implement ConfigLoader YAML parsing [HARNESS]
  test(M3-RT): add input-parser unit tests [HARNESS]
  fix(M3-RT-PERSIST-01): fix missing boundary-value validation [HARNESS]

Rules:
  - The [HARNESS] tag is used only for code generated by AI agents
  - The task-id must match the plan.md WBS ID (grammar: .harness.toml [task_id].regex — multi-segment allowed)
  - On session recovery, find the last checkpoint with git log --grep=HARNESS
```

---

## 8. Coding Conventions (per language)

- **Python**: [docs/coding-convention/Python.md](docs/coding-convention/Python.md)
- **JavaScript/TypeScript** (optional): [docs/coding-convention/JavaScript.md](docs/coding-convention/JavaScript.md)
- **C** (optional): [docs/coding-convention/C.md](docs/coding-convention/C.md)
- **Common (language-agnostic) quality rules**: [.clauderules](.clauderules)

---

## 9. Core Principles Summary

1. **Agent-First**: delegate domain tasks to specialist agents
2. **Test-Driven**: write tests before implementation, {{COVERAGE_THRESHOLD}}%+ coverage
3. **Security-First**: no compromises on secrets/input validation
4. **Immutability**: no object mutation, always return a new object
5. **Plan Before Execute**: for complex features, implement only after plan approval in Phase 2

---

## 10. Actions Requiring Explicit User Approval (Hard Gates)

| Gate | Approval keyword |
|--------|------------|
| Starting Phase 3 | The user explicitly says "start implementation" or a similar instruction |
| **Starting implementation (RED/GREEN) while the skeleton review has not passed** | **Forbidden** — only implement the body after the skeleton + R0 review PASS with CRITICAL/HIGH=0 (never implement before passing) |
| Phase 5 production deployment | `[RELEASE APPROVED]` |
| Modifying a safety boundary (`.harness.toml [safety_boundary]`) | User confirmation required |
| Destructive actions (rm -rf, force-push, DB drop) | User confirmation required |
| Committing a secret/credential | Absolutely forbidden |

---

## 11. Multi-Agent Collaboration (Single Writer / Independent Reviewer)

> This kit supports a collaboration where **one agent implements (Single Writer) and a second agent verifies as an independent reviewer** —
> e.g. **Claude implements ↔ Codex reviews independently** (or Gemini / another Claude instance).
> The governance **single source = [docs/ai-workflow/codex_claude_review_protocol.md](docs/ai-workflow/codex_claude_review_protocol.md)**.

- **Activation**: `.harness.toml [review_overlay].enabled = true`.
- **Roles**: implementer = modifies only within the `plan.md` DoD scope / independent reviewer = read-only independent verification by default / user = final decider.
- **Insertion points R0–R4**: R1 (RED tests) and R2 (Green diff) are required; safety boundaries, DB, migrations, and shutdown sequences go through all of R0–R4.
- **No concurrent writing**: do not put two writers on the same task at once (implement → halt → review → fix).
- **Handoff**: pasting a chat prompt is standard, **first line = `[PROMPT-ID: <TASK>_<STAGE>_<TYPE>_<YYYYMMDD>_<NN>]`**. Review source text = `docs/ai-workflow/reviews/`, scores/audits = `docs/ai-workflow/scores/`.
- **The second agent (e.g. Codex) reads this AGENTS.md as its entry point** and participates in the reviewer role of the protocol above.

---

## 12. Multi-Engine Harness: Roles, Write Scope & Universal Rules

> **This section applies to ALL engines** (Claude, Codex, Gemini).
> When an engine starts any task, it must read §12 first and comply unconditionally.
> Engine-specific detail files: `CODEX.md` (Codex raw exec) · `GEMINI.md` (Gemini doc tasks).

### 12.1 Engine Role Assignment

| Engine | Role | Can Write | Cannot Write |
|--------|------|-----------|-------------|
| **Claude** | Orchestrator — drives harness loop, plans, verifies, manages git | Orchestration scope (`progress.md`, `scores/`, `reviews/`) + code only when acting as implementer | Safety boundaries without user approval |
| **Codex** | Independent Reviewer (default) + Implementer when explicitly delegated — Stage 1 RED / Stage 2 GREEN / Stage 5 FIX via `.codex/agents/` named agents | Only files explicitly listed in the active task's DoD when acting as implementer; read-only when reviewing | `docs/**`, `.claude/**`, `.codex/**`, `.harness.toml`, build configs, CI files, `AGENTS.md`, `CODEX.md` |
| **Gemini** | Documentation Writer — docs/wiki generation only | `docs/**` except governance files listed in §12.5 | `src/**`, `tests/**`, `scripts/**`, `.harness.toml`, `AGENTS.md`, `CODEX.md`, `GEMINI.md`, `.claude/**`, `.codex/**`, `*.toml`, `.github/**` |

### 12.2 Universal Rules (ALL engines, no exceptions)

1. **6-Stage Quality Gate** — every code change passes all 6 stages before commit (`docs/_harness/quality-gates.md`)
2. **Safety Boundaries** — `.harness.toml [safety_boundary].paths` = STUB ONLY for every engine
3. **`[HARNESS]` tag** — all AI-generated code commits must carry this tag (§7)
4. **No unilateral commits** — no engine commits without an explicit user instruction
5. **git hygiene** — run `git diff --name-status` before finishing; report every changed path; revert any out-of-scope change before reporting
6. **No deletes** — never delete a file unless the prompt contains an explicit `DELETE LIST:` with that exact path
7. **Session recovery** — read `docs/ai-workflow/progress.md` first on every cold start (§2 above)

### 12.3 "WRITE SCOPE IS CLOSED" Protocol

When Claude delegates any task to Codex or Gemini, the handoff prompt **must** open with:

```
WRITE SCOPE IS CLOSED.
Read AGENTS.md §12 and CODEX.md (or GEMINI.md) before starting.

You may create or modify ONLY these paths:
- <path 1>
- <path 2>

You must not create, modify, delete, format, or normalize any other file.
After finishing, run: git diff --name-status
Report every changed path. Revert any out-of-scope change before reporting.
Do not commit.
```

Omitting this header from a raw `codex exec` or Gemini call is an operator error — not a model error.

### 12.4 Stage-by-Stage Engine Assignment

The 6-stage gate runs regardless of which engine implements the task:

| Stage | Primary Engine | Notes |
|-------|---------------|-------|
| 1 RED (write tests) | **Codex** (`test-writer.toml`) or Claude | Stage 1 output = `tests/` only; `src/` is read-only |
| 2 GREEN (implement) | **Codex** (`impl-coder.toml`) or Claude | Stage 2 output = `src/` only; `tests/` is read-only |
| 3 VERIFY (auto run) | **Claude** (runs `pytest` + `mypy`) | Shell only; no file writes |
| 4 REVIEW (parallel) | **Claude + Codex** in parallel | Read-only for both; findings written to `scores/` |
| 5 FIX | **Codex** (`refactor-fixer.toml`) or Claude | Scope limited to `findings[]` from Stage 4 |
| 6 AUDIT | **Claude** (`score-auditor` agent) | Read-only + writes to `scores/` only |

### 12.5 Gemini-Specific Rules

- Gemini is a **Documentation Writer only** — it does not write code, run tests, or commit.
- All Gemini output is **reviewed by Claude** before any commit.
- Gemini prompt template must include the "WRITE SCOPE IS CLOSED" header (§12.3) with a docs-only allowlist.
- Governance files that Gemini may **never** touch even within `docs/`:
  `docs/_harness/**`, `docs/ai-workflow/progress.md`, `docs/ai-workflow/plan.md`,
  `docs/ai-workflow/scores/**`, `docs/ai-workflow/reviews/**`
- See `GEMINI.md` for the full constraint file.
