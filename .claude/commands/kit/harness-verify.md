---
description: "Automatically runs the 6-stage harness quality gate — Stage 3 VERIFY → Stage 4 REVIEW (parallel) → Stage 5 FIX loop → Stage 6 AUDIT. Stages 1/2 (RED/GREEN) must be done manually beforehand with test-writer/impl-coder."
argument-hint: "<task_id> [test_paths] [src_paths]"
---

# /kit:harness-verify — automatic chaining of quality-gate Stages 3–6

Invoked right after the user completes Stage 1 (RED, test-writer) + Stage 2 (GREEN, impl-coder). This command automatically chains Stages 3–6 and records the results in `{{SCORES_DIR}}/<task_id>.json` + `.verify.json`.

> This document is the **single source for the stage → agent/script mapping**. To change the mapping, change it here only. (This automation drives the **Unit ring** only; the Module/Integration rings run separately — [compositional-verification.md](../../../docs/_harness/compositional-verification.md).)

| Stage | Performed by | Output |
|:--|:--|:--|
| 3 VERIFY | `scripts/harness_run_verify.sh` (Layer A) | `{{SCORES_DIR}}/<task_id>.verify.json` |
| 4 REVIEW | `code-reviewer` + `security-reviewer` (parallel, global agents) | findings[] JSON |
| 5 FIX | `refactor-fixer` (limited to findings scope) | append to `{{SCORES_DIR}}/<task_id>.json` |
| 6 AUDIT | `score-auditor` (re-run comparison) | append to `{{SCORES_DIR}}/<task_id>.json` |
| Commit guard | `scripts/harness_gate_check.sh` → `scripts/harness_audit_rerun.py` (PreToolUse hook, Layer C) | block / pass |

## Inputs
- `$1` = task_id (e.g. `{{TASK_ID_EXAMPLE}}`)
- `$2` = test paths (space-separated, e.g. `{{TESTS_ROOT}}/unit/test_<module>.py {{TESTS_ROOT}}/unit/test_<other>.py`)
- `$3` = the **dotted-module path** of src (e.g. `pkg.subpkg`) — for the coverage `--cov` target

## Execution Order

### Step 1 — Stage 3 VERIFY (automatic)
```bash
bash scripts/harness_run_verify.sh "$1" "$2" "$3"
```
- Generates `{{SCORES_DIR}}/<task_id>.verify.json`
- On failure, halt immediately → report the failing items to the user
- Note: the `--cov` target must be passed as a **dotted-module** (`pkg.subpkg`). Passing a filesystem path
  (`{{SRC_ROOT}}/pkg/mod.py`) makes coverage report a false 0%, and the Stage 6 re-run
  reproduces that false 0% verbatim, neutralizing the gate.

### Step 2 — Stage 4 REVIEW (parallel)
In a single message, **invoke two Task tools at once**:
- `Agent(subagent_type="code-reviewer", ...)`
- `Agent(subagent_type="security-reviewer", ...)`  ← confirm the global definition is read-only (if it has write permission, that is a matrix violation)

Pass to each agent:
- Target files (test + src)
- plan.md DoD citation
- Reuse the existing verify.json
- Return format: `{"score": "int", "findings": ["..."], "categories": {}}`

### Step 3 — Stage 5 FIX (conditional loop)
If either review has **score < 95** or **CRITICAL/HIGH > 0**:
- Invoke `Agent(subagent_type="refactor-fixer", ...)`
- Pass the full findings[] JSON
- After completion, **re-run Step 2** (up to 3 loops)

If still failing after 3 → escalate to the user (record a blocker in progress.md)

### Step 4 — Stage 6 AUDIT
- Invoke `Agent(subagent_type="score-auditor", ...)`
- Pass all of the previous stages' JSON artifacts
- Perform re-run verification:
  - Re-run pytest_cmd → passed matches
  - Re-run mypy_cmd → errors match
  - Re-run coverage_pct → within ±0.5% (confirm dotted-module target)
  - grep-confirm citations[].file:line
  - Detect permission-matrix violations via git diff + git status (including working-tree stragglers)
- Append to `{{SCORES_DIR}}/<task_id>.json`

### Step 5 — Final recording + guidance
- In `progress.md`, move "active task" → "last completed"
- Present a draft commit message:
  ```
  feat(<task_id>): <desc> [HARNESS]
  ```
- When the user runs `git commit`, `scripts/harness_gate_check.sh` (→ `harness_audit_rerun.py`, PreToolUse hook) re-verifies automatically

## Pass-Criteria Summary

| Stage | Threshold |
|:------|:----:|
| 3 VERIFY | binary pass (all pass) |
| 4 REVIEW | ≥ 95 AND CRITICAL=0 AND HIGH=0 |
| 5 FIX | scope compliance + 0 regressions |
| 6 AUDIT | ≥ 95 AND hallucination_flags=[] |

## On Failure

- Stage 3 failure → the user fixes it directly and re-invokes
- Stage 4 3-loop failure → recommend re-invoking planner
- Stage 6 hallucination detected → block the commit immediately, flag "HALLUCINATION" in progress.md

## Example

```
/kit:harness-verify {{TASK_ID_EXAMPLE}} "{{TESTS_ROOT}}/unit/test_<module>.py" "pkg.subpkg"
```
