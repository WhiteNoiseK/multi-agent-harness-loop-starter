# Independent Reviewer (Single Writer / Independent Reviewer) Protocol

<!-- ROLE BANNER: R0~R4 independent-reviewer overlay — an optional extension of the core 6-stage gate.
     What this document decides: the roles/timing/output format of the Single Writer and the Independent Reviewer.
     What this document does NOT decide: the 6-stage threshold scores (= docs/_harness/quality-gates.md). -->

> Applies to: any implementation work in {{PROJECT_NAME}} where one agent implements (Single Writer) and another agent
> participates as the independent reviewer (e.g., **Claude implements ↔ Codex reviews independently**, or another
> Claude instance). Enabled via `.harness.toml [review_overlay].enabled`.
> Purpose: fix each agent's work timing, review timing, and output format to prevent simultaneous edits to the same file and authority confusion.
> **Ring scope**: this R0~R4 overlay reviews the **Unit ring** loop; `R4 CLOSE` = Unit-ring closure, *not* trusted-unit promotion. The Module/Integration rings run separately — [`../_harness/compositional-verification.md`](../_harness/compositional-verification.md).

---

## 1. Conclusion

Default operation = **Single Writer / Independent Reviewer**.

- The Single Writer edits tests/code/docs within the scope of `plan.md` DoD.
- The Independent Reviewer **independently** examines the diff/tests/authority-doc consistency right after implementation.
- Do not put two writers in the same implementation loop at once (a dirty worktree and authority confusion cost more).

---

## 2. Role Division

| Role | Owner | Permissions |
|:---|:---|:---|
| Implementer (Single Writer) | primary agent | edit tests/code/docs within the scope of `plan.md` DoD |
| Independent Reviewer | secondary agent | read-only review by default. Can edit within a limited scope if the user explicitly says so |
| Final decision-maker | user | safety boundary, production deployment, scope expansion, rollback approval |

### Independent Reviewer Core Principles
- Unless the user says "fix it", prioritize reviewing over editing code.
- Review criteria = `plan.md` DoD, single-authority spec, the actual diff, test results.
- Even when also tasked with fixes, do not revert the implementer's changes and edit the minimum number of files.

---

## 3. Common Pre-Review Hook

When a review is requested, always reconstruct state in the order below.

```text
1. Read AGENTS.md / CLAUDE.md
2. Read docs/ai-workflow/progress.md
3. Read the current M-task section of docs/ai-workflow/plan.md
4. Read the recent relevant log in docs/ai-workflow/implementation_log.md
5. git log --oneline --grep=HARNESS -5
6. git status --short
7. git diff --stat
8. git diff --name-only
```

For data-schema-related work, additionally read the single-authority spec (`docs/engineering/...`).

---

## 4. Review Insertion Points (R0~R4)

| Point | Trigger | Reviewer Role | Block Criteria |
|:---|:---|:---|:---|
| R0: Skeleton Review | right after the skeleton commit | whether the skeleton/docstring reflects the DoD and authority docs | hold RED on CRITICAL/HIGH |
| R1: RED Test Review | after writing tests, before implementing | whether the tests actually catch the DoD failure | hold GREEN if a core DoD is unverified |
| R2: Green Diff Review | after implementation + unit verification | review the code/test diff | no commit on CRITICAL/HIGH |
| R3: Fix Verification | after fixing findings | confirm CRITICAL/HIGH are resolved | re-fix if unresolved |
| R4: Checkpoint Audit | just before/after commit | confirm commit scope/log/progress sync | hold on out-of-scope edits or log mismatch |

By default, **R1 and R2 are mandatory**; choose R0/R3/R4 based on risk.

**Safety-boundary tasks, DB schemas, migrations, and shutdown sequences run all of R0~R4.**
Safety-boundary paths (`.harness.toml [safety_boundary].paths`):

```text
{{SAFETY_BOUNDARY_PATHS}}
```

---

## 5. Implementer → Reviewer Handoff Format

The standard is to provide the handoff as a **prompt the user can paste into chat**.
In `implementation_log.md`, leave only a summary + artifact path; do not duplicate the original.

**Convention — the first line of every implementer↔reviewer prompt starts with a PROMPT-ID** (for tracking/re-request management):
`[PROMPT-ID: <TASK>_<STAGE>_<TYPE>_<YYYYMMDD>_<NN>]` — increment `NN` when re-requesting the same prompt.

```markdown
[PROMPT-ID: {{TASK_ID_EXAMPLE}}_R2_REVIEWREQ_{{YYYYMMDD}}_01]

## Review Request

- Task: {{TASK_ID_EXAMPLE}} {name}
- Stage: R0 Skeleton | R1 RED Test | R2 Green Diff | R3 Fix Verification | R4 Checkpoint Audit
- Last checkpoint: {git hash} {commit title}
- Changed files:
  - path/to/file.py
- Authority docs:
  - docs/...
- Verification already run:
  - command: result
- Known risks:
  - risk or "none"
- Review scope:
  - must check ...
  - out of scope ...
```

---

## 6. Review Result Format

Findings-first format. Regardless of PASS/BLOCKED, if there are substantive findings, keep the original in `docs/ai-workflow/reviews/`.

```markdown
## Review Result

Verdict: PASS | BLOCKED
Stage: R0 | R1 | R2 | R3 | R4
Task: {{TASK_ID_EXAMPLE}}
Artifact: docs/ai-workflow/reviews/{{TASK_ID_EXAMPLE}}_{R-stage}_review.md

### Findings
- [CRITICAL] file:line — issue
  Evidence: ...
  Required fix: ...

### Test Gaps
- ...

### Scope Notes
- Out-of-scope changes: none | yes
- Authority-doc conflicts: none | yes

### Recheck Command
- command to rerun
```

Severity meanings:
- `CRITICAL`: safety, data corruption, safety-boundary breach, migration corruption, production risk. Must be fixed.
- `HIGH`: DoD not met, tests fail to catch a core failure, possible runtime error. Must be fixed.
- `MEDIUM`: a structure/maintenance issue that can wait until the next task. Record it in the log.
- `LOW`: wording/comment/small cleanup. Defer if needed.

### 6.1 Review Original Retention Rules
- Storage location: `docs/ai-workflow/reviews/`
- Filename: `<task_id>_<review_stage>_review.md`
- Required sections: `Verdict`, `Stage`, `Task`, `Findings`, `Test Gaps`, `Authority Conflicts`, `Scope Notes`, `Recheck Command`
- If `BLOCKED`, you must not omit `Evidence` and `Required fix`.
- Record score/status/summary findings in `docs/ai-workflow/scores/<task_id>.json`.

---

## 7. Handoff Medium (RECONCILED)

> **Standard = pasting a chat prompt.** The default flow is the user directly passing one agent's output prompt
> to the next agent.
>
> **The inbox files in `handoffs/` (CODEX_INBOX/CLAUDE_INBOX) are deprecated** — not used in the default flow.
> Use them as a temporary aid only when the user explicitly requests "leave it as an inbox file".
>
> **Single source of truth for audit truth**:
> - Review originals = `docs/ai-workflow/reviews/`
> - Score/audit meta = `docs/ai-workflow/scores/`
>
> In `implementation_log.md`, leave only the path + summary.

---

## 8. Pass/Block Rules

If any of the following apply, the implementer must not commit.

- `Verdict: BLOCKED`
- one or more CRITICAL
- one or more HIGH
- a core DoD test is missing
- edits outside the files allowed by `plan.md`
- conflict with a single-authority spec
- a change to the safety boundary (`.harness.toml [safety_boundary].paths`) without user approval

The user may explicitly override, but the override reason must be recorded in `implementation_log.md`.

---

## 9. No Simultaneous Work

Two agents must not edit code at the same time on the same task.

Allowed flow:
```text
implementer edits → implementer stops → reviewer reviews → implementer fixes
```

Even in exceptions (when the user explicitly hands over), the reviewer first checks the change scope with `git diff --name-only`
and does not touch unrelated changes.
