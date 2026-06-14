# Lifecycle Standard

> **The standard procedure for an ideal development process.** Trial and error is inevitable, but this is the
> backbone document that decides in advance *what you must have nailed down by which point, and what risk follows
> if you don't*.
> Per-gate checklists are in [PHASE_GATES.md](PHASE_GATES.md); drift locking is in [DRIFT_LOCK.md](DRIFT_LOCK.md).

---

## 0. The Core Lesson in One Line

> **For instrumentation/systems software, the "contract" comes before the "pipeline" — not the other way around.**
> The pipeline is merely a *means* of satisfying the contract, so when the contract wobbles, the whole pipeline wobbles.
> Therefore, **freeze the three contracts (data definition · output sink · identifier/unit) before starting the pipeline**,
> or, if you can't, **isolate them behind an abstract boundary (facade)**. A contract that is neither frozen nor isolated = "the cost of going back to square one".

What sets this standard apart from every other methodology is that it institutionalizes that lesson as **Gate P (the three-contract freeze gate)**.

---

## 1. A Synthesis of Three Frames

This standard fuses three things into one:

| Frame | Contribution | Limitation (on its own) |
|:--|:--|:--|
| **PMBOK** process groups | Macro control: Initiating → Planning → Executing → M&C → Closing | No code-level execution loop |
| **VHCP** 6 phases | Document-driven + Agile nimbleness (research → plan → impl → delivery → deploy → retro) | Weak on the *pre-start* stages (Research/Feasibility) |
| **Harness 6-stage gate** | Enforces code quality (RED → GREEN → VERIFY → REVIEW → FIX → AUDIT) | Doesn't cover macro ordering / contract freezing |

→ Synthesis result = **8 stages**. The macro frame (PMBOK) is the skeleton, VHCP is the document flow, and the harness gate is the engine inside Executing.

```
            [S0 RESEARCH]          ← pre-start
                 │ Gate R
            [S1 INITIATING]        ┐
                 │ Gate I          │ PMBOK Planning group
            [S2 FEASIBILITY]       │
                 │ Gate F          │
            [S3 PLANNING] ★★★      ┘  ← Gate P = freeze the 3 contracts (the heart of this standard)
                 │ Gate P
            [S4 EXECUTING]  ←──┐   ← harness 6-stage gate loop (per task)
                 │ (per-task)  │
            [S5 MONITOR&CTRL] ─┘   ← cross-cutting control (progress/scores/audit)
                 │ Gate D → Gate S
            [S6 CLOSING/DELIVERY]  ← delivery_log + ★ Gate S (security audit) + [RELEASE APPROVED] + deployment_log
                 │
            [S7 REVIEW/ASSET]      ← lessons_learned + memory promotion
```

---

## 2. Definition of Each Stage

### S0 — RESEARCH (pre-start research) · VHCP Phase 1
- **Purpose**: Eliminate technical uncertainty before implementation + identify risks. *Read the codebase/domain/standards deeply* and analyze.
- **Deliverable**: `docs/ai-workflow/research.md` (PART A product/standards · B data · C architecture · D implementation guide · E risks · F legacy analysis).
- **Reuse first**: Before writing anything new, investigate existing implementations in this order: GitHub code search → official docs → package registries.
- **Gate R**: research.md complete + **at least 3 risks stated explicitly**. ⚠ research.md holds *analysis/history only* — never put data contracts here (they would become a second source alongside the spec later).

### S1 — INITIATING · PMBOK Initiating
- **Purpose**: Agree on what/why/how-far you will build. Declare boundaries for external dependencies (HW/subcontractor/vendor API).
- **Deliverable**: `docs/pm-guide/ProductProposal.md` (charter) + scope/boundary declaration.
- **Gate I**: charter + scope + **explicit external-dependency boundaries** (e.g., a hardware driver such as FPGA goes only as far as stub/mock, deferred until the vendor API is finalized).

### S2 — FEASIBILITY TEST (core-technology feasibility) · newly codified
- **Purpose**: Prove, before starting the pipeline, that *the core technology physically satisfies the hard requirements*.
- **Method**: For each core-technology claim, either ① a HW-in-the-loop spike (`scripts/verify_*.py` + a dated experiment report) **or** ② a quantitative simulation/trade study + an adoption threshold. Unresolved items become a **vendor question list** (no implicit assumptions).
- **Deliverables**: `docs/experiments/*_spike_report.md`, `docs/engineering/*_sim.md` / `*_trade_study.md`.
- **Gate F**: every core-technology claim has a spike/study result OR a facade + vendor question.
- *Real example*: With instrumentation equipment + an oscilloscope + signal-analysis tooling, we verified the frequency response down to each measurement segment and only then started formal development — this stage was done well. Conversely, the fact that an external device's fixed latency (hundreds of ms) threatened the target measurement cycle (1 Hz) was discovered in a spike. **You want to discover that here, not at integration time — it's far cheaper.**

### S3 — PLANNING ★★★ THE FREEZE GATE · VHCP Phase 2 + PMBOK Planning
- **Purpose**: Establish the WBS + DoD. And, above all, **freeze the three contracts the pipeline depends on.**
- **Deliverables**: `plan.md` (WBS in 2–4h units + per-task DoD + verification commands + functional spec) + **three contract documents at v1.0** + a legacy-leak audit when cloning.
- **Gate P (hard gate — no entering Executing until it's green)**:
  1. **Data-definition contract** = `_TEMPLATE_data_spec.md` at v1.0 "Authoritative" (every column: unit · formula · range · normal/boundary/failure value).
  2. **Output-sink contract** = the CSV/DB/FTP/hybrid choice is finalized **or** the StorageService facade interface (`write_*`) is fixed on day 1 (swapping the backend storage has no impact on callers).
  3. **Identifier/unit contract** = `_TEMPLATE_identifier_unit_contract.md` (internal-ID ↔ external-ID Mapper, ts unit epoch-ms/s, angle range, anchor constants declared).
  4. (For clone projects) **legacy-leak audit** `_TEMPLATE_assumption_leak_audit.md` passes.
- *If a value is genuinely undecided*: instead of a guessed real value, place a **documented placeholder/facade + guard** (e.g., leave a column whose formula is undecided as a `0.0` placeholder with a "do not persist as a real value" guard). Don't let a guessed value flow through as if it were real.
- *Real example (the cost of skipping this)*: The realtime/aggregate specs were frozen at v1.0 long after the build began → corrections to the angle value range, one column's formula, and the column count (47↔46) became multi-file rework. The StorageService was redefined in v2 from "CSV append → 3 tiers", which revealed the complete absence of a realtime persistence path. The internal-index ↔ external-identifier Mapper and epoch ms/s were only nailed down at M3-2x. **All three were drift that Gate P should have blocked.**

### S4 — EXECUTING · VHCP Phase 3
- **Purpose**: Incremental delivery of code whose integrity is proven. **A 6-stage gate loop per task.**
- **Loop**: RED (test-writer, tests/ only) → GREEN (impl-coder, src/ only) → VERIFY (run_verify.sh) → REVIEW (code + security in parallel) → FIX (refactor-fixer, findings scope) → AUDIT (score-auditor re-run). Safety boundaries get an independent-reviewer R0–R4 overlay.
- **Pass**: each stage meets its threshold + CRITICAL/HIGH = 0 + hallucination_flags = [].
- **Forward build**: in data-flow order (M1 infrastructure → M2 adapters → M3 core → M4 frontend → M5 integration). External-dependency tasks are deferred with explicit stub/mock (an intentional facade at the build-order level). *("M5 integration" is a build-order **milestone**, not the verification **Integration ring** — [../_harness/compositional-verification.md](../_harness/compositional-verification.md) §0.)*
- Details: `docs/_harness/quality-gates.md`.

### S5 — MONITORING & CONTROLLING · cross-cutting, runs alongside S4 · PMBOK M&C
- **Purpose**: Prevent claimed ≠ actual + make drift visible.
- **Means**: the `progress.md` ledger + the `scores/*.json` audit trail + score-auditor in-session re-runs + working-tree straggler checks + an assumption audit before entering any major sub-stage.

### S6 — CLOSING / DELIVERY · VHCP Phase 4–5 · PMBOK Closing
- **Gate D (delivery QA)**: full suite + coverage + mypy green. Monkey Testing ("you never know what a user will do"). `delivery_log.md` QA report.
- **Gate S (pre-deployment security audit — release-blocking)**: a **whole-system** security pass over the release candidate (secrets scan over the full tree · dependency vulnerability scan · input/boundary validation · authN/authZ · injection/output · error/log leakage · transport/storage · attack surface) with **0 unresolved CRITICAL/HIGH**, and no per-task Stage 4 security finding left deferred. This is a *separate sector* from the per-task Stage 4 `security-reviewer` — it catches what only appears once the pieces are assembled into a deployable whole. Sign off in `delivery_log.md`. Details: [PHASE_GATES.md](PHASE_GATES.md) Gate S · `security_gate.md`.
- **Deployment gate (hard)**: production requires an explicit **`[RELEASE APPROVED]`** approval + a citation of the delivery verification number **that cites a passed Gate S**. Record in `deployment_log.md`.

### S7 — REVIEW / ASSETIZATION · VHCP Phase 6
- **Deliverables**: `docs/retrospective/lessons_learned.md` + **promotion to agent memory (MEMORY.md)**. *(This **memory promotion** is distinct from the verification ladder's **trusted-unit promotion** — [../_harness/compositional-verification.md](../_harness/compositional-verification.md) §3.)*
- ⚠ In the original project, lessons_learned was left empty and the learnings accumulated only in memory — fill both and cross-link them.

---

## 3. PMBOK ↔ VHCP ↔ This Standard Mapping

| PMBOK process group | VHCP Phase | This standard's stage |
|:--|:--|:--|
| (pre-start) | Phase 1 Research | **S0 Research** |
| Initiating | — | **S1 Initiating** (newly codified) |
| Planning | Phase 2 Plan | **S2 Feasibility** (new) + **S3 Planning / Gate P** |
| Executing | Phase 3 Impl | **S4 Executing** (6-stage gate) |
| Monitoring & Controlling | (implicit) | **S5 M&C** (newly codified) |
| Closing | Phase 4 Delivery / 5 Deploy | **S6 Closing/Delivery** |
| Closing | Phase 6 Retro | **S7 Review/Asset** |

> **What this standard adds to VHCP**: the Initiating stage (S1), core-technology feasibility (S2), explicit control (S5),
> and above all **Gate P's three-contract freeze rule**. The original project did these three informally/late and paid the price.

## 4. Cross-Cutting Invariant Principles (apply to all stages)

- **Contract first**: freeze the contracts (data/sink/identifier) before the code, or isolate them behind a facade.
- **Single authoritative document**: one canonical spec per domain. Conflicts are resolved at read time by authority/recency (`CLAUDE.md §8` + Foam `_authority.md`).
- **Single source of truth (SSOT)**: the same value/setting lives in one place (`.harness.toml`, `pyproject.toml`). No duplication (the root of drift).
- **Reuse first**: investigate existing implementations/libraries before writing anything new.
- **No stopgaps**: discard what's wrong immediately + correct it in one sweep. A deprecated gradual migration = two systems coexisting.
- **Security at two layers**: per task (Stage 4 `security-reviewer`, every change) **and** once per release (Gate S whole-system audit before the production push). Security is also the 4th axis of every option scorecard (`recommendation_policy.md` §1).
- **Stability above all**: in a hard-to-access/high-availability environment, errors are absolutely forbidden > recoverability > visibility > maintainability > performance.
