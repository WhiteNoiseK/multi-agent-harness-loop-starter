---
description: "Tri-engine recommendation under the kit's recommendation policy (4-column scorecard: stability / security / maintainability / visibility, plus the no-temporary-fixes gate). Claude + Codex + Antigravity each produce an independent scorecard, then synthesize. Latency-optimized: Claude dispatches Codex & Antigravity first, then scores itself while they run. Append a focus area to weight that axis (e.g. 'security-focused', 'migration risk')."
argument-hint: "[optional: an axis or target to weight — e.g. 'security-focused', 'performance of this file', 'migration risk']"
---

# /kit:recommend — tri-engine recommendation (Claude + Codex + Antigravity)

<!-- Three-engine panel: Claude + Codex + Antigravity (`agy`). agy is a READ-ONLY recommend scorer here
     (logic only, no pytest — like Codex's scorecard). This is its SECOND role; its primary role is the
     headless documentation writer. agy is still NOT a code reviewer — the R0-R4 code-review loop stays
     Claude (Writer) ↔ Codex (Reviewer). See AGENTS.md §12. -->

Produce a recommendation for the decision / options / target currently under discussion.
**Claude, Codex, and Antigravity each score independently, then synthesize.** This always runs as a
three-engine panel — no flag needed.

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

## 1. Execution flow (latency-optimized — dispatch Codex & Antigravity FIRST, then self-review while waiting)

### Step 1 — Dispatch Codex AND Antigravity first (parallel, background)

**Before** Claude writes its own scorecard, immediately fire **both** Codex and Antigravity with
**`run_in_background: true`** in the **same message** (true parallel) so their latency overlaps Claude's
own scoring. Do NOT block on them yet.

**No artificial timeout.** A backgrounded engine sends a completion notification when it genuinely
finishes — wait for that, do not wrap it in `timeout`. Cutting off a slow-but-valid review to "move on"
is a stopgap that drops the verification (and violates §0 "no temporary fixes"). The only reason to stop
an engine early is a *true hang* (no completion notification **and** the process shows no CPU progress) —
then `TaskStop` it and treat it as a §4 fallback.

The handoff is a self-contained **ASCII-English** brief — the decision context, the options, and the
evaluation criteria. **Do NOT include Claude's scores** (each engine scores from first principles).
Both engines are **READ-ONLY** here: they must not modify/create/delete any file.

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

```powershell
# Antigravity (agy) — run_in_background: true, SAME message as Codex (true parallel). NO timeout wrapper.
# agy = the 3rd scorer. Call it through the wrapper, NEVER `agy -p` directly: on Windows agy's transcript
# writer loses the reply when cwd is on a different DRIVE than HOME (see
# docs/ai-workflow/antigravity_automation_setup_guide.md §3). The wrapper forces a same-drive cwd + clean
# EOF stdin + one-argv prompt + explicit --model and prints the reply from the transcript.
#   (a) write the SAME brief body used for codex (the [RECOMMEND REVIEW] block above) to a UTF-8 temp file:
#         Set-Content -LiteralPath "$env:TEMP\agy_brief.txt" -Value $brief_text -Encoding utf8
#   (b) dispatch the wrapper (read-only scoring → no -AddDir needed):
& ".\scripts\agy_ask.ps1" -PromptFile "$env:TEMP\agy_brief.txt" -Model 'Gemini 3.1 Pro (High)'
# Output = the scorecard between '=== AGY REPLY START ===' / '=== AGY REPLY END ===',
#          or a single 'AGY_UNAVAILABLE: <reason>' line -> treat agy as unavailable (§4 fallback).
```

### Step 2 — While it runs, Claude scores (solo)

Without waiting, Claude produces its own scorecard + pick for each option:

| Option | Stability | Security | Maintainability | Visibility | Temp fix? |
|:--|:--|:--|:--|:--|:--|

One recommendation + grounds (which axis it wins on) + why rejected options lose.
If `$ARGUMENTS` names a focus axis/target, re-evaluate weighting it — if the conclusion changes, say why.
This work overlaps the engines' latency (the whole point of Step 1 first).

### Step 3 — Collect Codex + Antigravity

When the background tasks return, read each engine's **own** independent scorecard + pick (Antigravity's
reply = the text between `=== AGY REPLY START ===` / `=== AGY REPLY END ===` in the wrapper output; if it
printed `AGY_UNAVAILABLE: <reason>` instead, treat agy as unavailable per §4). After each returns,
**verify it stayed read-only** (`git status` unchanged vs. before) — per the engine roles, Codex and
Antigravity are read-only in the panel.

### Step 4 — Synthesis (three engines)

**Unanimous** (all three pick the same option):
> Shared pick with combined grounds — cite the axis all three agreed on.
> Confidence: "Very high — all three engines agree on [axis]."

**Majority** (2 of 3 agree):
> Go with the majority pick, but **name the dissenting engine and the exact axis it diverges on**.
> If the dissent is on the **top axis (stability)** or touches a **safety boundary** →
> **escalate to the architect** as a judgmental decision despite the majority (do not auto-pick).

**Three-way split** (all different) → **escalate to the architect**. Show all three scorecards side by side:

| Axis | Claude | Codex | Antigravity |
|:--|:--|:--|:--|
| Stability | … | … | … |
| Security | … | … | … |
| Maintainability | … | … | … |
| Visibility | … | … | … |
| Temp fix? | … | … | … |
| **Pick** | Option X | Option Y | Option Z |

> Name the exact axes of divergence. Do NOT average scores or auto-pick.

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

## 4. Fallback (per engine)

Each external engine is independent — if one is unavailable, still deliver the others.
- **Codex** unavailable (`codex exec` fails / not wired / true hang → `TaskStop`) → state so, proceed with Claude + Antigravity.
- **Antigravity** unavailable (`agy` not installed / not logged in, or the wrapper printed `AGY_UNAVAILABLE: <reason>`) → state so, proceed with Claude + Codex.
- **Both** external engines fail → deliver Claude's solo scorecard, flag the bridge failure, offer to retry.
A slow review is **not** a failure: wait for it. Never silently skip an engine — always state which engines actually scored and why any did not.

> Cross-refs: `docs/pm-guide/recommendation_policy.md` · `AGENTS.md §12` (engine roles — Codex/Antigravity
> read-only in the panel; agy is NOT a code reviewer) · `docs/ai-workflow/antigravity_automation_setup_guide.md`
> (the agy wrapper) · `docs/ai-workflow/codex_loop_operating_policy.md` (the 5 stop axes).
