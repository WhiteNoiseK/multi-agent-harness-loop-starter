---
description: "Dual-engine recommendation under the kit's recommendation policy (4-column scorecard: stability / security / maintainability / visibility, plus the no-temporary-fixes gate). Claude + Codex each produce an independent scorecard, then synthesize. Latency-optimized: Codex is dispatched first, then Claude scores while it runs. Append a focus area to weight that axis (e.g. 'security-focused', 'migration risk')."
argument-hint: "[optional: an axis or target to weight — e.g. 'security-focused', 'performance of this file', 'migration risk']"
---

# /kit:recommend — dual-engine recommendation (Claude + Codex)

<!-- Two-engine panel: Claude + Codex. The kit's third engine (Antigravity, `agy`) is the headless
     documentation writer and is NEVER a panel reviewer — do not add it here (see AGENTS.md §12). -->

Produce a recommendation for the decision / options / target currently under discussion.
**Claude and Codex each score independently, then synthesize.** This always runs as a
two-engine panel — no flag needed.

## 0. Fixed criteria (the recommendation policy — do not change)

- **4-column scorecard required**: **stability · security · maintainability · visibility (readability)**. Never omit an axis.
- **Priority (tiebreaker)**: **stability first** > security > maintainability > visibility.
- **No temporary fixes**: no deprecate-and-migrate that leaves two systems coexisting — discard the wrong thing
  and correct cleanly in one pass. (Score this as the **5th column** — `Temp fix?` — on every option; a masking
  workaround such as skip/xfail/swallow is a violation, honest deferral of an unrelated bug is not.)
- **No "natural flow" hand-waving** — justify each axis with explicit grounds.
- **Single-authority spec values are not options** (they are to be complied with). Only open questions
  (process / wiring / spec refinement) become options.

Authority: `docs/pm-guide/recommendation_policy.md` (the scorecard + the auto-verification policy).

## 1. Execution flow (latency-optimized — dispatch Codex FIRST, then self-review while waiting)

### Step 1 — Dispatch Codex first (background)

**Before** Claude writes its own scorecard, immediately fire Codex with **`run_in_background: true`**
so its latency overlaps Claude's own scoring. Do NOT block on it yet.

**No artificial timeout.** A backgrounded engine sends a completion notification when it genuinely
finishes — wait for that, do not wrap it in `timeout`. Cutting off a slow-but-valid review to "move on"
is a stopgap that drops the verification (and violates §0 "no temporary fixes"). The only reason to stop
an engine early is a *true hang* (no completion notification **and** the process shows no CPU progress) —
then `TaskStop` it and treat it as a §4 fallback.

The handoff is a self-contained **ASCII-English** brief — the decision context, the options, and the
evaluation criteria. **Do NOT include Claude's scores** (Codex scores from first principles).
Codex is **READ-ONLY** here: it must not modify/create/delete any file.

```
# CRITICAL — end the codex dispatch with `< /dev/null`. `codex exec` reads stdin and APPENDS it to the
# prompt; under run_in_background the stdin pipe never receives EOF, so the engine BLOCKS at
# "Reading additional input from stdin..." BEFORE processing the prompt (indistinguishable from a hang —
# it never produces output). `< /dev/null` gives immediate EOF.
# Also: read the background output FILE directly to observe progress — NEVER pipe through `tail`
# (tail buffers until the process exits, so you see nothing until the very end / forever if blocked).

# Codex — run_in_background: true, --skip-git-repo-check, `< /dev/null`. NO timeout wrapper.
codex exec --skip-git-repo-check "
[RECOMMEND REVIEW]
Decision: <one-line description>
Options: <A, B, C …>
Context: <relevant constraints from plan.md / research.md>
Criteria: stability · security · maintainability · visibility · no-temporary-fixes (stability = highest priority tiebreaker)
Task: Score each option on all 5 axes (High/Medium/Low + brief reason), pick one, explain why.
Score from first principles. READ-ONLY: do not modify any file. Be concise.
" < /dev/null
```

### Step 2 — While it runs, Claude scores (solo)

Without waiting, Claude produces its own scorecard + pick for each option:

| Option | Stability | Security | Maintainability | Visibility | Temp fix? |
|:--|:--|:--|:--|:--|:--|

One recommendation + grounds (which axis it wins on) + why rejected options lose.
If `$ARGUMENTS` names a focus axis/target, re-evaluate weighting it — if the conclusion changes, say why.
This work overlaps Codex's latency (the whole point of Step 1 first).

### Step 3 — Collect Codex

When the background task returns, read Codex's **own** independent scorecard + pick.
After it returns, **verify it stayed read-only** (`git status` unchanged vs. before) —
per the engine roles, Codex is read-only in the panel.

### Step 4 — Synthesis (two engines)

**Agreement** (both pick the same option):
> Shared pick with combined grounds — cite the axis both agreed on.
> Confidence: "High — both engines agree on [axis]."

**Disagreement** (different winners) → show both scorecards side by side:

| Axis | Claude | Codex |
|:--|:--|:--|
| Stability | … | … |
| Security | … | … |
| Maintainability | … | … |
| Visibility | … | … |
| Temp fix? | … | … |
| **Pick** | Option X | Option Y |

> Name the **exact axis they diverge on** and why. Do NOT average scores or auto-pick.
> If divergence is on the **top axis (stability)** or touches a **safety boundary** →
> **escalate to the architect** as a judgmental decision.

## 2. Stop / confirm needed

List separately (do not proceed unilaterally):
- **Trust-collapse**: claimed != actual / no fact layer
- **Safety boundary**: schema/migration · secret · real-HW · single-authority spec
- **Judgmental decision**: frozen test · scope expansion · contract reversal
- **Spec/authority conflict**: defer to the architect — no auto-ranking
- **Engine divergence on stability axis or safety boundary** → escalate

## 3. Proceed rule (when code changes are involved)

On an explicit "proceed as recommended" from the architect → run the internal 6-stage gate
(REVIEW parallel + FIX loop + AUDIT) through to commit.

**Severity is not a stop axis** — findings (incl. >= HIGH) self-heal in the FIX loop. Stops are only the
§2 axes above.

## 4. Fallback

If Codex is unavailable (session not wired / `codex exec` fails / true hang → `TaskStop`) → state so
explicitly, deliver Claude's solo scorecard, and offer to retry when the bridge is available. A slow
review is **not** a failure: wait for it. Do not silently skip Step 1.

> Cross-refs: `docs/pm-guide/recommendation_policy.md` · `AGENTS.md §12` (engine roles — Codex is
> read-only in the panel) · `docs/ai-workflow/codex_loop_operating_policy.md` (the 5 stop axes).
