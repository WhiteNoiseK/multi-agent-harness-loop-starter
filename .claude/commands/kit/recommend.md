---
description: "Recommendation under the kit's recommendation policy (4-column scorecard: stability / security / maintainability / visibility + no temporary fixes). Append a focus area to weight that axis, or `--with-codex` for an independent second opinion on complex/high-stakes decisions."
argument-hint: "[--with-codex] [optional: an axis or target to weight — e.g. 'security-focused', 'performance of this file', 'migration risk']"
---

# /kit:recommend — recommendation under the recommendation policy

Produce a recommendation for the decision / options / target currently under discussion, using the
**recommendation policy**. If `$ARGUMENTS` is present, **weight that perspective/target**; otherwise balance
the four axes in priority order.

## 0. Fixed criteria (the recommendation policy — do not change)

- **4-column scorecard required**: **stability · security · maintainability · visibility (readability)**. Never omit an axis.
- **Priority (tiebreaker)**: **stability first** > security > maintainability > visibility.
- **No temporary fixes**: no deprecate-and-migrate that leaves two systems coexisting — discard the wrong thing
  and correct cleanly in one pass.
- **No "natural flow" hand-waving** — justify each axis with explicit grounds.
- **Single-authority spec values are not options** (they are to be complied with). Only open questions
  (process / wiring / spec refinement) become options.

Authority: `docs/pm-guide/recommendation_policy.md` (the scorecard + the auto-verification policy).

## 1. Output format

1. If there is more than one option — a per-option **4-column table** + a "temporary fix?" column:

   | Option | Stability | Security | Maintainability | Visibility | Temp fix? |
   |:--|:--|:--|:--|:--|:--|

2. **One recommendation** + grounds (which axis it wins on) + why the rejected options lose.
3. If `$ARGUMENTS` names a focus axis/target, **re-evaluate weighting it** — if the conclusion changes, say why.
4. **Stop / confirm needed** (if any, listed separately): trust-collapse (claimed != actual / no fact layer) ·
   safety boundary (schema/migration · secret · real-HW · single-authority spec) · judgmental decision
   (frozen test · scope expansion · contract reversal) · spec/authority conflict (defer to the architect — no auto-ranking).

## 2. Proceed rule (when code changes are involved)

- On an explicit "proceed as recommended" → run the internal 6-stage gate (REVIEW parallel + FIX loop + AUDIT)
  through to commit.
- **Severity is not a stop axis** — findings (incl. >= HIGH) self-heal in the FIX loop. Stops are only the
  §1.4 axes (trust-collapse · safety-boundary · judgmental · authority-conflict · retry-exhaustion 3x).

## 3. Optional: `--with-codex` — independent second opinion (complex / high-stakes decisions)

By default the recommendation is Claude's (Single Writer) alone. Append `--with-codex` to also get the
Independent Reviewer's (Codex) own evaluation, then synthesize both. The extra step runs **only** when the
flag is present.

1. Claude produces its own 4-column scorecard + pick (as in §1).
2. Claude writes a self-contained **ASCII-English handoff** — the decision, the options, and Claude's
   scorecard — and sends it to the reviewer via the headless bridge (`scripts/run_codex_review_bridge.py` /
   `codex exec`, read-only; setup: `docs/ai-workflow/codex_automation_setup_guide.md`). Requires the review
   overlay wired (a session id); if it is not, say so and fall back to the solo recommendation.
3. The reviewer returns its **OWN independent 4-column scorecard + pick** — it must score the axes itself,
   not echo Claude's.
4. Claude **synthesizes**:
   - **Agreement** → the shared pick with the combined grounds (higher confidence).
   - **Disagreement** → show **both scorecards side by side** and name the exact axis they diverge on. Do
     NOT average them away. If they diverge on the top axis (stability) or on a safety boundary, **escalate to
     the architect** as a judgmental decision — do not auto-pick.

This is the *perspective-diverse verify* pattern applied to a **decision** (not an implementation): two
independent scorecards beat one, and a disagreement is itself the most useful signal. The reviewer reviews
logic only (no code execution) — `--with-codex` is for the *decision*, not a fact check (that belongs to
`/kit:auto-harness`).

> Cross-refs: `docs/pm-guide/recommendation_policy.md` · `docs/ai-workflow/codex_loop_operating_policy.md` (the 5 stop axes).
