---
description: "Drives the Claude (Single Writer) <-> independent-reviewer (e.g. Codex) review round-trip automatically via headless `codex exec`, running the current task's current stage to close (through R4 CLOSE if the task is mid-flight). No copy-paste. Task-agnostic."
argument-hint: "[task_id]"
---

# /kit:auto-harness -- automatic Claude <-> Codex review loop (closes the current stage of the current task)

When the user invokes `/kit:auto-harness`, drive the Claude (Single Writer) <-> Codex (Independent Reviewer)
review round-trip automatically -- with no copy-paste -- via headless `codex exec`, for **whatever the current
active task is**, until **the current stage closes** (and, if the task is mid-flight, through R4 CLOSE). This is a
general-purpose command, independent of the task type.

This overlay is an optional extension of the core 6-stage gate. Enable it per project in `.harness.toml`
`[review_overlay] enabled = true`. The independent-reviewer contract lives in
`docs/ai-workflow/codex_claude_review_protocol.md` -- this command is the executor for that protocol.

Argument: `/kit:auto-harness [task_id]` -- if omitted, use the current active task in `progress.md`.

> **FIRST-RUN GATE (before §0).** Check `.harness.toml [review_overlay].stop_points_acknowledged`. If it is not
> `true`, **do NOT start the loop.** First present the current stop-points to the operator -- `severity_auto_max`,
> `fact_layer_required`, the **5 STOP axes** (authoritative list: `docs/ai-workflow/codex_loop_operating_policy.md`
> §3), and the current `[safety_boundary].paths` (flag it if still empty) -- and ask them to approve running with
> these as-is. On explicit approval, set `stop_points_acknowledged = true`, then proceed. Once true, the
> stop-points and the choice not to change them are the operator's responsibility (policy §0); the loop runs
> strictly per `.harness.toml` and never silently alters a threshold.

## 0. Resume procedure (always first, once the gate above is satisfied)

1. End of `{{PROGRESS_FILE}}` -> identify the current active task + the pending stage / verdict
2. `{{SCORES_DIR}}/<task_id>.json` -> identify the last stage recorded
3. `git log --oneline --grep=HARNESS -5` -> last checkpoint
4. If there is a handoff queued to send, send that first; if Codex enclosed the next prompt in its previous
   reply, use that as the next input.

## 1. Codex round-trip (validated pattern)

Headless `codex exec` resumes a single persistent reviewer session and captures its verdict to a file --
no copy-paste, no clipboard.

```powershell
$h    = "<absolute path to the handoff .md>"   # docs/ai-workflow/handoffs/*.md (ASCII English, self-contained)
$tmp  = Join-Path $env:TEMP "codex_scratch"; New-Item -ItemType Directory -Force $tmp | Out-Null
$reply = Join-Path $tmp "reply_<NN>.txt"
Get-Content -LiteralPath $h -Raw -Encoding utf8 |
  codex exec --sandbox read-only --skip-git-repo-check -C $tmp -o $reply resume <SESSION_ID> -
Get-Content -LiteralPath $reply -Raw -Encoding utf8
```

- `<SESSION_ID>` = the persistent Codex reviewer session id (one per project; record it in your project notes
  or `.harness.toml`/local config). The first run creates it; subsequent runs `resume` it.
- **running review (default)**: mount `<REPO_PATH>` (your repo root) with `-C` so Codex reads and verifies the
  real code directly. Note: this sends the repo to the reviewer provider -- only enable if that is within your
  project's data-handling policy. Keep `--sandbox read-only` = the reviewer cannot write. **handoff-only**
  (empty scratch dir) is the alternative when reviewing design docs only and the repo must not leave the machine.
  Options must come **before** `resume`. Permission: settings.json must allow `"Bash(codex exec:*)"` (if absent,
  ask the user -- do not self-grant).
- **The reviewer cannot re-run locally** -> fact-checking = local (the orchestrator / score-auditor re-runs
  pytest/mypy/ruff directly). The gate is the reviewer verdict **AND** claimed==actual, both.

## 2. Stage loop (start at whatever stage you are in, proceed from there)

```
R0 design (research / scores)        <-> codex (PASS / ADJUST; rerun after self-heal)
 -> R1 RED (test-writer; independent re-verify)        <-> codex (PASS / BLOCKED)
 -> R2 GREEN (impl-coder) -> self-Stage4 (code + security review, parallel) -> Stage5 FIX (self-heal findings)
                                                       <-> codex (PASS / BLOCKED)
 -> Stage6 AUDIT (score-auditor, +/-0 match) -> [HARNESS] commit (in-scope only, 0 stragglers)
 -> R4 handoff after the commit          <-> codex (CLOSE / RE-OPEN) -> on CLOSE: stop and report
```

Stage <-> agent/script mapping is owned by `docs/_harness/quality-gates.md` and `/kit:harness-verify`;
Claude subagents already exist at `.claude/agents/{test-writer,impl-coder,refactor-fixer,score-auditor}.md`.

- PROMPT-ID: received N -> emit N+1 (global, monotonic). Handoff = ASCII, self-contained (synthesize the
  cumulative journey so far, not just the current stage -- the headless reviewer is stateless). User-facing
  report = the user's language.
- Distrust agent self-reports -- the orchestrator re-runs directly (3-layer: agent claim -> local re-run ->
  reviewer verdict). Verify the pass/fail distribution per test name, not just the totals.
- Refresh `{{PROGRESS_FILE}}` / scores at every stage transition.

## 3. Gate policy

- **Severity is NOT a stop axis** -- all findings (including CRITICAL / HIGH) go through the internal
  self-heal FIX loop. The 6-stage gate (`docs/_harness/quality-gates.md`) is the arbiter.
- **Stop conditions -- the 5 STOP axes** (authoritative list: `docs/ai-workflow/codex_loop_operating_policy.md` §3):
  1. **Trust collapse** -- `claimed != actual` (a self-report disagrees with the orchestrator's local re-run),
     no fact layer to check against, or an unhygienic handoff payload (mojibake / missing contract field).
  2. **Self-heal retries exhausted** -- 3 attempts at the same stage without passing.
  3. **Safety boundary** -- a change inside a `.harness.toml [safety_boundary]` path, OR a real
     hardware / external-device / production action (those are supervised + manual only; never automated).
     Generic boundary examples: `"**/migrations/**"`, `"**/*secret*"`, `".env*"`, `"**/order*"`.
  4. **Judgmental decision** -- editing a frozen test, expanding beyond task scope, or changing a
     contract/interface other components depend on.
  5. **Single-authority spec / doc conflict** -- a single source of truth disagrees; defer to the architect
     (code != spec means the code is wrong -> auto-fix, but a genuine authority-vs-authority conflict stops).
- **5-priority order, always**: stability > security > maintainability > visibility (readability), plus
  **no temporary fixes** (fix it cleanly once; no deprecate-and-migrate that leaves two systems coexisting).
- No full suite (scoped tests only — the scoped run = the **Unit ring**; the Module/Integration rings run separately, see [compositional-verification.md](../../../docs/_harness/compositional-verification.md)). `[HARNESS]` commit / R4 CLOSE = **Unit-ring closure**, not trusted-unit promotion. Preserve out-of-scope dirty / uncommitted changes (user-edited files join
  in their own task, not this one).

## 4. Completion report

On stage / task CLOSE, report in the session chat: the per-stage Codex verdict history (the PROMPT-ID chain),
commit SHA(s), key defects (found -> fixed -> verified), and the next stage. `{{PROGRESS_FILE}}` / scores remain
the permanent audit trail.
