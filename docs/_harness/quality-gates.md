# Quality Gates — Harness Scored Loop (vendored)

> **source:** global `~/.claude/rules/common/quality-gates.md` · **kit baseline v0.1.0** (for kit_version tracking).
> This file is the **vendored (self-contained)** 6-stage spec inside the kit — it works even without the global copy.
> If it diverges from the global copy, this file is the single source of truth within the kit, and operational values must match `.harness.toml [gates]`.
> Documentation language = `.harness.toml [language] docstring_lang` (default English; Korean (or other) projects set docstring_lang accordingly).

> This file defines the criteria for running **code → review → test → fix** as a
> scored 6-stage loop in harness engineering mode.
> Each stage must clear its **threshold score** before advancing to the next; if it falls short, a dedicated
> agent performs the fix. To prevent hallucination, per-stage permission separation plus meta-audit is
> mandatory.

> **Path tokens**: `{{SRC_ROOT}}` / `{{TESTS_ROOT}}` / `{{SCORES_DIR}}` come from `.harness.toml [paths]`
> (substituted by `harness_init.py`). Thresholds come from `.harness.toml [gates]`.

---

## 0. Loop Structure (6 stages + preceding R0)

> **Preceding hard gate (R0 Skeleton)**: *Before* the 6 stages below, each new src file starts as a docstring + signature **skeleton** and receives an architect (+ security, when a safety boundary is involved) review. **Do not begin (1) RED or implementation until the skeleton review PASSES (CRITICAL/HIGH = 0)** — a stage that catches design flaws and missing features *before any code is written*, using comments alone. (Rationale: `.clauderules` Skeleton-First · `docs/ai-workflow/codex_claude_review_protocol.md` R0)

```
┌──────────────────────────────────────────────────────────┐
│  (1) RED       test-writer     →  write tests (confirm failure) │
│       │                                                   │
│       ▼                                                   │
│  (2) GREEN     impl-coder      →  minimal implementation (tests pass) │
│       │                                                   │
│       ▼                                                   │
│  (3) VERIFY    harness_run_verify.sh → automated verification (pytest) │
│       │                                                   │
│       ▼                                                   │
│  (4) REVIEW    code-reviewer + security-reviewer          │
│       │                                                   │
│       ▼                                                   │
│  (5) FIX       refactor-fixer  →  address review findings  │
│       │                                                   │
│       ▼                                                   │
│  (6) AUDIT     score-auditor   →  re-verify scores (meta)  │
│       │                                                   │
│       └─── pass ──→  commit [HARNESS]  →  next task        │
│       └─── fail ──→  return to (1) (retry_count++)         │
└──────────────────────────────────────────────────────────┘
```

> **Ring scope** ([compositional-verification.md](compositional-verification.md)): this 6-stage loop automates the **Unit ring** — Stage 3 VERIFY runs **scoped unit tests**. The **Module / Integration rings** (real-boundary; emulator/device) run **outside** this loop. `commit [HARNESS]` = **Unit-ring closure**, *not* trusted-unit promotion (which waits for the Integration ring passing).

---

## 1. Per-Stage Scoring Criteria

> Threshold source = `.harness.toml [gates]` (red_threshold / green_threshold / review_threshold /
> audit_threshold / coverage_threshold). The numbers below are the kit baseline defaults.

### Stage 1 — RED (write tests): threshold ≥ 90

| Item | Points | Criterion |
|:-----|:----:|:-----|
| DoD coverage | 30 | Every requirement in the plan.md DoD is expressed as a test |
| Boundary conditions | 25 | Includes normal + boundary + failure + timeout cases |
| Isolation | 20 | External dependencies accessed only via Mock/fixture |
| Naming | 15 | `test_<subject>_<condition>_<expected>` pattern |
| Intended RED | 10 | Before implementation, `pytest -x` fails with AssertionError/Import error |

### Stage 2 — GREEN (minimal implementation): threshold ≥ 85

| Item | Points | Criterion |
|:-----|:----:|:-----|
| Tests pass | 40 | 100% of the task's tests pass |
| Type safety | 20 | mypy strict 0 errors |
| Complexity | 15 | Functions ≤ 50 LOC, cyclomatic complexity ≤ 10 |
| docstring | 15 | File/function docstrings present (readable by non-engineers, language = docstring_lang) |
| Minimality | 10 | No features added beyond what the tests require |

### Stage 3 — VERIFY (automated verification): **binary pass/fail**

All must pass to advance (performed by `scripts/harness_run_verify.sh`):
- [ ] `pytest {{TESTS_ROOT}}/unit/test_<module>.py -v` → 0 failed (collection errors also count as failures)
- [ ] `--cov=<dotted.module> --cov-fail-under=80` → pass — **the `--cov` target is a dotted-module path**
      (e.g. `pkg.subpkg`). Passing a filesystem path (`{{SRC_ROOT}}/pkg/mod.py`) makes coverage
      report a **false 0%**, and the Stage 6 re-run reproduces that false 0%, neutralizing the gate.
- [ ] `mypy {{SRC_ROOT}}/<module>` → 0 errors
- [ ] `ruff check {{SRC_ROOT}}/<module>` → 0 errors
- [ ] `black --check` → 0 changes needed

### Stage 4 — REVIEW: threshold ≥ 95 AND CRITICAL=0 AND HIGH=0

| Item | Points | Criterion |
|:-----|:----:|:-----|
| CRITICAL = 0 | 25 | No security/data-loss/race-condition issues — **even one fails immediately** |
| HIGH = 0 | 25 | No logic errors/resource leaks — **even one fails immediately** |
| Readability | 20 | Naming, function decomposition, nesting depth ≤ 4 |
| Reusability | 15 | Duplication removed, appropriate abstraction |
| Test–implementation alignment | 15 | Tests cover the actual implementation path |

**Pass condition**: `score ≥ 95 AND critical_count == 0 AND high_count == 0`
**Execution**: code-reviewer + security-reviewer **in parallel (2)** (invoke both Tasks in the same message)

### Stage 5 — FIX: limited to the review scope

- refactor-fixer modifies only the files/lines listed in the Stage 4 review JSON `findings[]`
- Out-of-scope modifications are rejected by score-auditor
- All CRITICAL/HIGH findings must be 100% resolved (even one unresolved → fail)
- After FIX, **re-run Stage 4** (up to 3 loops; if still failing after 3, escalate to the user)

### Stage 6 — AUDIT (meta verification): threshold ≥ 95 AND hallucination_flags=[]

score-auditor **re-runs the previous stages within the session** to verify their results:
- Re-run `pytest_cmd` → `pytest_result.passed/failed/skipped` must match exactly (±0)
- Re-run `mypy_cmd` → `mypy_errors` must match exactly (±0)
- Re-run `ruff_cmd` → `ruff_errors` must match exactly (±0)
- Re-parse coverage → `coverage_pct` within ±0.5% (confirm dotted-module target)
- grep-confirm `citations[].file:line` exist (if absent, add a hallucination_flag)
- Use `git diff --name-only` + `git status` to detect permission-matrix violations + working-tree stragglers
- Scan the DoD checklist for missing items

**Pass condition**: `score ≥ 95 AND status == "pass" AND hallucination_flags == [] AND permission_matrix_violations == []`

Any mismatch → record in `hallucination_flags[]` + `status: "fail"` + **block commit**

**PreToolUse hook re-verification (Layer C)**: `scripts/harness_gate_check.sh` (shim) → `scripts/harness_audit_rerun.py`
runs automatically on a `git commit ... [HARNESS]` command:
1. Load `{{SCORES_DIR}}/<task_id>.json`
2. Verify the AUDIT entry (score ≥ 95, status == pass, hallucination_flags == [])
3. Re-run `pytest_cmd` → confirm claimed == actual (last line of defense)

> The task-id extraction grammar is owned by `docs/_harness/TASK_ID_GRAMMAR.md`, and `harness_audit_rerun.py`
> follows that grammar (`.harness.toml [task_id] regex`) — no literal duplication. Multi-segment IDs (e.g. `M3-RT-PERSIST-01`) also match.

Emergency bypass: `HARNESS_SKIP_GUARD=1` environment variable (user's responsibility, logged as WARN)

---

## 2. Permission Matrix (hallucination prevention)

| Agent | Write {{TESTS_ROOT}}/ | Write {{SRC_ROOT}}/ | Write docs/ | Run pytest | Role |
|:---------|:-----------:|:---------:|:----------:|:-----------:|:-----|
| test-writer | ✅ | ❌ (read only) | ❌ | ✅ (RED verification) | Stage 1 |
| impl-coder | ❌ (read only) | ✅ | ❌ | ✅ (GREEN verification) | Stage 2 |
| harness_run_verify.sh | ❌ | ❌ | ✅ ({{SCORES_DIR}}/) | ✅ (read-only) | Stage 3 |
| code-reviewer | ❌ | ❌ | ❌ | ✅ (read-only) | Stage 4 |
| security-reviewer | ❌ | ❌ | ❌ | ✅ (read-only) | Stage 4 |
| refactor-fixer | ✅ (review scope) | ✅ (review scope) | ❌ | ✅ | Stage 5 |
| score-auditor | ❌ | ❌ | ✅ ({{SCORES_DIR}}/) | ✅ (re-run) | Stage 6 |
| harness_gate_check.sh → harness_audit_rerun.py (PreToolUse hook) | ❌ | ❌ | ❌ | ✅ (re-run) | Layer C |

**Key point**: test-writer and impl-coder can each write only to their own area → this forces the implementation
to conform to the tests and blocks the reverse bias of tests being warped to fit the implementation.

---

## 3. Agent Handoff JSON Schema

At the end of each stage, append the following JSON to `{{SCORES_DIR}}/<task_id>.json`:

```json
{
  "task_id": "{{TASK_ID_EXAMPLE}}",
  "stage": "RED|GREEN|VERIFY|REVIEW|FIX|AUDIT",
  "agent": "test-writer|impl-coder|...",
  "score": 92,
  "threshold": 90,
  "status": "pass|fail",
  "retry_count": 0,
  "artifacts": {
    "files_written": ["{{TESTS_ROOT}}/unit/test_<module>.py"],
    "files_modified": [],
    "pytest_result": {"passed": 12, "failed": 0, "skipped": 0},
    "coverage_pct": 87.3,
    "mypy_errors": 0
  },
  "citations": [
    {"file": "{{SRC_ROOT}}/<path>/<module>.py", "line": 42, "note": "..."}
  ],
  "findings": [
    {"severity": "HIGH", "file": "...", "line": 10, "rule": "...", "fix_hint": "..."}
  ],
  "timestamp": "<ISO8601>"
}
```

---

## 4. Retry / Escalation Rules

| Situation | Action |
|:-----|:-----|
| Stage 1–2 below threshold once | Retry the same agent (pass feedback JSON) |
| Same task fails 3 times in a row | **Escalate to the user** (record a blocker in progress.md) |
| 5 cumulative failures | **Re-invoke planner** (split/redesign the task) |
| Stage 3 environment issue (import failure, etc.) | Bring in **build-error-resolver** |
| Stage 4 CRITICAL found | **In-depth re-review by security-reviewer** |
| score-auditor detects claimed vs. actual mismatch | **Halt immediately**, flag "HALLUCINATION" in progress.md + report to user |

---

## 5. Execution Example ({{TASK_ID_EXAMPLE}})

```bash
# Stage 1: invoke test-writer
# → create {{TESTS_ROOT}}/unit/test_<module>.py, confirm pytest fails

# Stage 2: invoke impl-coder
# → implement {{SRC_ROOT}}/<path>/<module>.py, pytest passes

# Stages 3–6: automatic chaining (--cov target is a dotted-module)
/kit:harness-verify {{TASK_ID_EXAMPLE}} "{{TESTS_ROOT}}/unit/test_<module>.py" "pkg.subpkg"

# On pass, commit (the PreToolUse hook re-verifies)
git commit -m "feat({{TASK_ID_EXAMPLE}}): <description> [HARNESS]"
```

---

## 6. Related Files

- `scripts/harness_run_verify.sh` — Stage 3 automated verification script (Layer A). **`--cov` dotted-module** + `HARNESS_SELFTEST` lock
- `scripts/harness_gate_check.sh` — PreToolUse commit guard shim (→ `harness_audit_rerun.py`)
- `scripts/harness_audit_rerun.py` — Layer C re-run verification logic (generalized for multi-segment task-ids)
- `docs/_harness/TASK_ID_GRAMMAR.md` — task-id grammar source of truth (followed by the commit guard)
- `.claude/commands/kit/harness-verify.md` — Stage 3–6 chaining slash command (single source for the stage→agent mapping)
- `docs/ai-workflow/progress.md` — task status tracking
- `{{SCORES_DIR}}/<task_id>.json` — per-stage score log (RED/GREEN/VERIFY/REVIEW×2/FIX/AUDIT)
- `{{SCORES_DIR}}/<task_id>.verify.json` — standalone Stage 3 VERIFY artifact
- `.claude/agents/test-writer.md` — Stage 1 dedicated agent (writes {{TESTS_ROOT}}/)
- `.claude/agents/impl-coder.md` — Stage 2 dedicated agent (writes {{SRC_ROOT}}/)
- `.claude/agents/refactor-fixer.md` — Stage 5 dedicated agent (limited to findings scope)
- `.claude/agents/score-auditor.md` — Stage 6 meta-audit agent (re-run based)

## 7. Execution Flow Summary

```
User invokes:
  1. Manually invoke test-writer (Stage 1 RED)
  2. Manually invoke impl-coder (Stage 2 GREEN)
  3. /kit:harness-verify <task_id> <test_paths> <dotted.module>
       ├─ Stage 3 VERIFY (harness_run_verify.sh)
       ├─ Stage 4 REVIEW (code-reviewer + security-reviewer in parallel)
       ├─ Stage 5 FIX (conditional: score<95 OR CRITICAL/HIGH>0, up to 3 loops)
       └─ Stage 6 AUDIT (score-auditor)
  4. git commit -m "feat(...): ... [HARNESS]"
       └─ harness_gate_check.sh → harness_audit_rerun.py PreToolUse hook re-verifies
```
