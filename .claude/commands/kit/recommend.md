---
description: "Recommendation under the kit's recommendation policy (4-column scorecard: stability / security / maintainability / visibility). Claude + Codex each produce an independent scorecard, then synthesize. Append a focus area to weight that axis (e.g. 'security-focused', 'migration risk')."
argument-hint: "[optional: an axis or target to weight — e.g. 'security-focused', 'performance of this file', 'migration risk']"
---

# /kit:recommend — dual-engine recommendation (Claude + Codex)

Produce a recommendation for the decision / options / target currently under discussion.
**Claude and Codex each score independently, then synthesize.** This always runs as a two-engine panel —
no flag needed.

## 0. Fixed criteria (the recommendation policy — do not change)

- **4-column scorecard required**: **stability · security · maintainability · visibility (readability)**. Never omit an axis.
- **Priority (tiebreaker)**: **stability first** > security > maintainability > visibility.
- **No temporary fixes**: no deprecate-and-migrate that leaves two systems coexisting — discard the wrong thing
  and correct cleanly in one pass.
- **No "natural flow" hand-waving** — justify each axis with explicit grounds.
- **Single-authority spec values are not options** (they are to be complied with). Only open questions
  (process / wiring / spec refinement) become options.

Authority: `docs/pm-guide/recommendation_policy.md` (the scorecard + the auto-verification policy).

## 1. Execution flow (always runs both engines)

### Step 1 — Claude's scorecard (solo, before seeing Codex)

Claude produces its own 4-column scorecard + pick for each option:

| Option | Stability | Security | Maintainability | Visibility | Temp fix? |
|:--|:--|:--|:--|:--|:--|

One recommendation + grounds (which axis it wins on) + why rejected options lose.
If `$ARGUMENTS` names a focus axis/target, re-evaluate weighting it — if the conclusion changes, say why.

### Step 2 — Codex's independent scorecard

Claude writes a self-contained **ASCII-English handoff** to Codex — the decision context, the options,
and the evaluation criteria (NOT Claude's scores — Codex must score independently). Send via:

```
codex exec "
[RECOMMEND REVIEW]
Decision: <one-line description>
Options: <A, B, C …>
Context: <relevant constraints from plan.md / research.md>
Criteria: stability · security · maintainability · visibility (stability = highest priority tiebreaker)
Task: Score each option on all 4 axes (High/Medium/Low + brief reason), pick one, and explain why.
Do NOT echo any score I might have — score from first principles.
"
```

Codex returns its **own independent 4-column scorecard + pick**. It must score the axes itself.

### Step 3 — Synthesis

**Agreement** (same winner):
> Shared pick with combined grounds — cite the axis both agreed on.
> State confidence level: "High confidence — both engines agree on [axis]."

**Disagreement** (different winners):
> Show **both scorecards side by side**:

| Axis | Claude | Codex |
|:--|:--|:--|
| Stability | … | … |
| Security | … | … |
| Maintainability | … | … |
| Visibility | … | … |
| **Pick** | Option X | Option Y |

> Name the **exact axis they diverge on** and why. Do NOT average scores or auto-pick.
> If divergence is on the top axis (stability) or touches a safety boundary →
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

If Codex is unavailable (session not wired / `codex exec` fails) → state so explicitly, deliver
Claude's solo scorecard, and offer to retry when the bridge is available. Do not silently skip Step 2.

> Cross-refs: `docs/pm-guide/recommendation_policy.md` · `docs/ai-workflow/codex_loop_operating_policy.md` (the 5 stop axes).
