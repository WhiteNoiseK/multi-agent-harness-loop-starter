# Codex Loop Operating Policy

<!-- ROLE BANNER: the operating policy for the automated Single-Writer / Independent-Reviewer loop.
     What this document decides: WHO does what, WHEN the loop auto-proceeds, and WHEN it must STOP.
     What this document does NOT decide:
       - the 6-stage threshold scores                 -> docs/_harness/quality-gates.md
       - the reviewer's R0-R4 timing / output format  -> docs/ai-workflow/codex_claude_review_protocol.md
       - how to wire up the headless reviewer CLI      -> docs/ai-workflow/codex_automation_setup_guide.md
       - task-id grammar                               -> docs/_harness/TASK_ID_GRAMMAR.md -->

> Applies to: any implementation work in {{PROJECT_NAME}} run as an automated review loop, where one agent
> implements (Single Writer) and a second, independent agent reviews (Independent Reviewer) until the
> current stage of the active task closes.
> Enabled via `.harness.toml [review_overlay].enabled = true`.
> This document is the single authority for the *loop's operating policy* (roles, auto-proceed, stop triggers).
> It does not redefine the 6-stage thresholds (those live in `docs/_harness/quality-gates.md`) or the
> reviewer's R0-R4 stage format (that lives in `docs/ai-workflow/codex_claude_review_protocol.md`).

---

## 0. First-Application Acknowledgement (REQUIRED before the first loop run)

The loop auto-proceeds and only stops on the criteria in this document. **Before this loop runs for the first
time in a project, the operator must see and approve those stop-points** — they must never be applied silently.

On the first `/kit:auto-harness` (while `.harness.toml [review_overlay].stop_points_acknowledged` is not `true`), the
agent's first action is NOT to start the loop. Instead it MUST:

1. **Present the current stop-point configuration** to the operator, in plain language:
   - `severity_auto_max` (from `.harness.toml [review_overlay]`) — the highest finding severity that
     auto-proceeds (and the fact that severity is otherwise *not* a stop axis — section 2).
   - `fact_layer_required` — whether a local re-run must confirm `claimed == actual`.
   - The **five STOP axes** (section 3) and the current `[safety_boundary].paths` that drive axis 3 (note when
     that list is still empty — the operator should fill it before relying on axis 3).
2. **Obtain the operator's explicit approval** to run the loop with these stop-points as-is.
3. **Record the approval** by setting `stop_points_acknowledged = true` in `.harness.toml [review_overlay]`.

Only after the flag is `true` does `/kit:auto-harness` start the review loop.

### Responsibility (made explicit)

Once acknowledged, the configured stop-points — **and the operator's choice not to change them** — are the
**operator's responsibility**. Concretely:

- The agent runs the loop **strictly per the approved `.harness.toml` configuration**. It never silently
  raises/lowers a threshold or removes a stop axis.
- If the operator leaves the thresholds unchanged, the operator accepts the consequences of the loop
  auto-proceeding (or stopping) per those approved criteria. Outcomes that follow from the operator's chosen,
  unchanged thresholds are the operator's responsibility, **not the agent's**.
- To change a stop-point, the operator edits `.harness.toml` directly (and may re-acknowledge). The agent will
  surface a *recommendation* to change a threshold when it has cause, but will not change it on its own.

---

## 1. Role Split: Single Writer / Independent Reviewer

| Role | Default agent | Authority |
|:---|:---|:---|
| Single Writer | the implementing agent (e.g. Claude) | edits tests / code / docs within the scope of `plan.md` DoD |
| Independent Reviewer | a second, independent agent (e.g. Codex, Gemini, or another instance) | read-only review by default; may edit only inside an explicit, user-named scope |
| Final decider | the human operator | safety boundaries, production deploy, scope expansion, rollback approval |

Principles:

- One writer per task. The Single Writer and the Independent Reviewer never edit the same file
  simultaneously. The allowed flow is: **Writer edits -> Writer stops -> Reviewer reviews -> Writer fixes.**
- The Single Writer already runs the internal 6-stage quality gate (RED -> GREEN -> VERIFY -> REVIEW ->
  FIX -> AUDIT) via its dedicated subagents (`.claude/agents/{test-writer,impl-coder,refactor-fixer,score-auditor}.md`).
  The Independent Reviewer **reads** those self-review artifacts (`docs/ai-workflow/scores/<task_id>.json`)
  and then **independently re-verifies** them — see `docs/ai-workflow/codex_claude_review_protocol.md`.
- The Reviewer's value is finding what the Writer's self-review *missed*, not echoing what it already
  caught. Same DoD, different lens.

---

## 2. The Auto-Proceed Model

The loop is designed to self-heal and keep moving. The default posture is **auto-proceed**, not
stop-and-ask.

```
R0 design (research/scores)        <-> reviewer (PASS/ADJUST; self-heal, then rerun)
  -> R1 RED   (test-writer; independent re-verify)        <-> reviewer (PASS/BLOCKED)
  -> R2 GREEN (impl-coder) -> self-REVIEW (Stage 4)
       -> self-FIX (Stage 5: findings feed the self-heal loop)
                                                            <-> reviewer (PASS/BLOCKED)
  -> AUDIT (Stage 6: score-auditor, claimed == actual, +/-0)
  -> [HARNESS] commit (in-scope only, zero stragglers)
  -> R4 handoff (commit first)     <-> reviewer (CLOSE/RE-OPEN) -> on CLOSE: stop & report
```

**SEVERITY IS NOT A STOP AXIS.** This is the core of the model:

- All findings — *including CRITICAL and HIGH* — feed the internal 6-stage self-heal FIX loop. A CRITICAL
  finding does **not** halt the loop and wait for the operator; it raises the FIX effort and triggers a
  re-run of Stage 4 REVIEW.
- Severity drives **how hard the FIX loop works**, never **whether the loop stops for the human**.
- A clean sub-MEDIUM result commits straight through. Stage 6 AUDIT is the backstop that auto-commits a
  self-healed result only when `claimed == actual`.

The loop stops for the human only on the five axes in section 3. Nothing else.

> **Opt-in override.** A high-stakes project may turn severity *into* a stop axis via
> `.harness.toml [review_overlay] severity_is_stop_axis = true` (with `severity_auto_max` as the
> threshold). The default is **off** — severity never stops the loop. `scripts/auto_gate.py` reads
> both knobs at runtime; the doctrine above is the default behavior, not a hardcoded rule.

---

## 3. STOP Triggers (the 5 axes)

The loop pauses and reports to the operator **only** when one of these five conditions is hit. (Severity is
deliberately absent — see section 2.)

1. **Trust collapse.** The ground-truth fact layer disagrees with the claim, or there is no fact layer to
   check against, or the handoff payload is unhygienic. Concretely:
   - `claimed != actual` — a self-reported score, pass count, or coverage number does not match the
     orchestrator's own re-run.
   - fact-layer none — a stage asserts a result with no re-runnable evidence behind it.
   - payload-hygiene — the handoff is mojibake / non-ASCII / missing a required contract field / the
     copy-paste prompt and the handoff file disagree.

2. **Retry exhaustion (3x).** The same stage's self-heal FIX loop has run three times without passing.
   Stop and escalate rather than loop forever.

3. **Safety boundary.** A change is needed inside a path the agent must not auto-modify, or a step needs a
   real hardware / external-device / production action. These require explicit human approval and, where
   applicable, an operator-supervised manual step — they are never automated.
   - Configure the exact paths per project in `.harness.toml [safety_boundary]`. Generic examples:
     `**/migrations/**`, `**/*secret*`, `.env*`, `**/order*` (anything touching schema/migration, secrets,
     real hardware drivers, or irreversible side effects).

4. **Judgmental decision.** A choice that is not the agent's to make: editing a frozen test, expanding
   beyond the task scope, or changing a contract/interface other components depend on.

5. **Spec / document-authority conflict.** The implementation disagrees with a single-authority spec or
   document. **Defer to the architect (human); do NOT auto-rank** which authority wins. (Note: when *code*
   simply disagrees with an authoritative *spec*, the spec wins and the agent auto-corrects the code — that
   is not a conflict and not a stop. The stop is for genuine authority-vs-authority ambiguity.)

Also enforced throughout:

- Scoped runs only — never a full suite when a scoped run answers the question.
- Out-of-scope dirty working-tree changes are preserved and left uncommitted (a human's direct edits join
  in their own task).

---

## 4. Two-Layer Gate: Logic AND Fact must BOTH pass

A stage advances only when **both** layers agree. A reviewer PASS alone is **never** sufficient.

| Layer | Who | What it proves |
|:---|:---|:---|
| Logic layer | Independent Reviewer | reasoned review of the diff, tests, and authority-doc consistency |
| Fact layer | the orchestrator's own re-run | `claimed == actual` for pytest/mypy/ruff/coverage, re-executed locally |

Why both:

- The Independent Reviewer typically **cannot run the project's local test suite** (it reviews logic, not
  execution). So fact verification is the orchestrator's job: re-run the gate commands locally and compare
  to what was claimed.
- Therefore the gate is: **reviewer verdict == PASS AND claimed == actual.** If the reviewer says PASS but
  the local re-run shows a different pass/fail distribution, that is a trust-collapse STOP (section 3, axis 1).
- Distribution matters: compare per-test-name pass/fail, not just the totals.

---

## 5. PROMPT-ID, Handoff Language, and User Report

- **PROMPT-ID convention.** Every prompt in the loop carries an id header. On receiving prompt N, the next
  output is N+1. The increment range covers paste/handoff prompts only (not casual chat, status, or
  tool-check turns).
- **Handoff = ASCII English, self-contained.** Files under `docs/ai-workflow/handoffs/*.md` are ASCII-only
  English Markdown (no HTML, no non-ASCII). Each handoff synthesizes the cumulative journey so a stateless
  reviewer can act on it without prior context. Rationale: headless reviewers and Windows cp949 viewers
  mojibake non-ASCII.
- **User report = the operator's language.** Copy-paste prompts shown to the human and the final report are
  written in the operator's working language. The handoff file and the user-facing prompt are the *same
  contract* expressed in two registers; they must not disagree (a disagreement is a payload-hygiene STOP).

---

## 6. The 5 Priorities (always in force)

When trading off any decision in the loop, apply this fixed ordering:

```
stability > security > maintainability > visibility  +  no temporary fixes
```

- **stability** — the system must not error; favor fail-loud over silent partial success.
- **security** — no hardcoded secrets, validated inputs, least privilege.
- **maintainability** — small focused files/functions, no speculative abstraction.
- **visibility** — readable code, observable behavior, clear naming.
- **no temporary fixes** — do not leave a deprecated path running alongside a new one. Fix it cleanly in
  one pass; two coexisting systems raise future correction cost.

These priorities are the tie-breaker the FIX loop uses while self-healing findings.

---

## 7. Headless Reviewer Round-Trip (reference)

The loop drives the Independent Reviewer without copy-paste via a headless CLI. The exact wiring (CLI
install, permissions, session id) is owned by `docs/ai-workflow/codex_automation_setup_guide.md`; the shape
of the call is:

```powershell
$h     = "<absolute path to handoff .md>"   # docs/ai-workflow/handoffs/*.md (ASCII English, self-contained)
$tmp   = Join-Path $env:TEMP "codex_scratch"; New-Item -ItemType Directory -Force $tmp | Out-Null
$reply = Join-Path $tmp "reply_<NN>.txt"
Get-Content -LiteralPath $h -Raw -Encoding utf8 |
  codex exec --sandbox read-only --skip-git-repo-check -C <REPO_PATH> -o $reply resume <SESSION_ID> -
Get-Content -LiteralPath $reply -Raw -Encoding utf8
```

- **Running review (default):** mount `<REPO_PATH>` with `-C` so the reviewer reads the real code directly.
  `--sandbox read-only` keeps the reviewer write-blocked. Options must precede `resume`. Mounting the repo
  sends it to the reviewer's provider — confirm this is within the operator's allowed disclosure scope.
- **Handoff-only review (alternative):** point `-C` at an empty scratch dir so only the design/handoff docs
  are reviewed and the repo never leaves the machine.
- `<SESSION_ID>` and `<REPO_PATH>` are placeholders — set them per project. Grant the CLI permission in the
  project settings (e.g. an allow-rule for `codex exec`); the agent cannot self-grant it.
- The reviewer cannot re-run locally -> the fact layer (section 4) is the orchestrator's local re-run.

---

## 8. Completion Report

When the current stage/task reaches CLOSE, report to the operator (in their language), in the chat:

- the per-stage reviewer verdict history (the PROMPT-ID chain),
- the commit SHA(s),
- the key findings (found -> fixed -> verified),
- the next stage.

`docs/ai-workflow/progress.md` and `docs/ai-workflow/scores/<task_id>.json` remain the permanent audit
trail; the chat report is the human-facing summary, not the system of record.

---

## 9. Cross-References

- `docs/ai-workflow/codex_automation_setup_guide.md` — how to install and wire the headless reviewer CLI.
- `docs/ai-workflow/codex_claude_review_protocol.md` — the Independent Reviewer's R0-R4 timing, handoff
  format, findings format, and pass/block rules.
- `docs/_harness/quality-gates.md` — the 6-stage gate thresholds (RED/GREEN/VERIFY/REVIEW/FIX/AUDIT) and
  the permission matrix.
- `docs/_harness/TASK_ID_GRAMMAR.md` — task-id grammar used in commits and handoffs.
- `.harness.toml` — single config seam: `[review_overlay].enabled` turns this loop on;
  `[safety_boundary].paths` defines the stop-axis-3 boundaries.
