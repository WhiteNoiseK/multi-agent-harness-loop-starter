# PHASE GATES — Per-Gate [Freeze / Risk / Mitigation] Checklist

> "By this point you should have nailed down up to here. If you don't, here are the risks ahead, so prepare for them."
> — all on one page. Each gate **must pass before moving to the next stage**.
> Stage definitions are in [lifecycle-standard.md](lifecycle-standard.md); drift is in [DRIFT_LOCK.md](DRIFT_LOCK.md).

Legend: 🟢 pass condition · 🔴 if you don't (a real case from the original project) · 🛡 mitigation (kit deliverable)

---

## Gate R — Research complete

- 🟢 `research.md` PART A–F written + **at least 3 risks stated explicitly** + reuse investigation of existing implementations/libraries done.
- 🔴 Starting a build on top of unknown requirements → if the premise is wrong, everything above it wobbles.
- 🛡 An empty `docs/ai-workflow/research.md` template (analysis/history only, no storing of contracts).

## Gate I — Initiating complete

- 🟢 charter (`ProductProposal.md`) + scope declaration + **explicit external-dependency boundaries** (HW/subcontractor/vendor API).
- 🔴 Scope creep / an undeclared HW dependency that explodes later.
- 🛡 `ProductProposal.md` charter scaffold + a "defer external-dependency tasks" build-order note.

## Gate F — Feasibility complete

- 🟢 For each core-technology claim, a spike (`verify_*.py` + experiment report) **or** a quantitative sim/trade study + an adoption threshold. Unresolved = vendor question list.
- 🔴 Discovering **only at integration time** that the core technology can't meet the hard requirements (an external device's fixed latency of hundreds of ms vs. the target measurement cycle of 1 Hz).
- 🛡 `experiments/_TEMPLATE_spike_report.md` · `engineering/_TEMPLATE_engineering_sim.md` · `_TEMPLATE_trade_study.md`.

---

## ★ Gate P — Planning / Three-Contract Freeze (hard gate — the heart of this standard)

> **No entering Executing (pipeline code) until the three contracts are green.**
> If a value is genuinely undecided, place a **documented placeholder/facade + guard** instead of a guessed real value.

| # | Contract to freeze 🟢 | If you don't 🔴 (real, from the original project) | Mitigation 🛡 |
|:--|:--|:--|:--|
| P-1 | **Data definition** = `_TEMPLATE_data_spec.md` v1.0 Authoritative (column · formula · unit · range · normal/boundary/failure value) | The spec v1.0 freeze came long after the build → corrections to the angle value range, one column's formula, and the column count (47↔46) caused **cascading rework** across reconstruction · schema · format · frontend | An empty data_spec scaffold (Changelog + authority declaration + §3.1 ```text header) |
| P-2 | **Output sink** = the CSV/DB/FTP/hybrid choice finalized **or** the StorageService facade (`write_realtime_row`/`write_stats10min`) fixed on day 1 | M3-08 "CSV append → 3 tiers" v2 redefinition → discovered the **complete absence of a realtime persistence path**, then re-wired the repository/session FKs | `_TEMPLATE_erd.md` (output sink + Mapper doctrine) |
| P-3 | **Identifier/unit** = internal-ID ↔ external-ID Mapper, ts epoch-ms/s, angle range, anchor constants | The internal-index ↔ external-identifier and epoch ms/s were only nailed down at M3-2x → a retroactive Mapper + a DB CHECK violation (270° → INSERT rollback = data loss) | `_TEMPLATE_identifier_unit_contract.md` (layered authority + anchor constants) |
| P-4 | (When cloning) **legacy-leak audit** passes | A previous project's assumptions (the prior domain's geometry/calibration constants) bleed into the new domain | `_TEMPLATE_assumption_leak_audit.md` (**required** when cloning) |
| P-0 | WBS in 2–4h units + per-task DoD + verification commands + functional spec | A weak, "make it work"–style completion criterion → endless re-checking | An empty `plan.md` template |

## Gate (per-task) — Executing 6 stages

- 🟢 **(prerequisite) R0 Skeleton review PASS (CRITICAL/HIGH = 0) — absolutely no starting RED/implementation until it passes** → RED ≥ 90 → GREEN ≥ 85 → VERIFY (binary) → REVIEW ≥ 95 ∧ CRITICAL = HIGH = 0 → FIX (scope) → AUDIT ≥ 95 ∧ hallucination_flags = []. Safety boundaries use Codex R0–R4. *(This per-task gate covers the **Unit ring**; `commit [HARNESS]` = Unit-ring closure. Module/Integration rings + trusted-unit promotion: [../_harness/compositional-verification.md](../_harness/compositional-verification.md).)*
- 🔴 Gate forgery (echo "7 passed"), the reverse bias where tests are bent to fit the implementation.
- 🛡 Permission-separated agents (tests/ only ↔ src/ only) + run_verify + commit-guard re-run (anti-forgery) + `quality-gates.md`.

## Gate D — Delivery (staging QA)

- 🟢 Full suite + coverage + mypy green + Monkey Testing + `delivery_log.md` QA report.
- 🔴 An unverified production push (irrecoverable in a hard-to-access environment).
- 🛡 `delivery_log.md` + an approval-token gate.

## ★ Gate S — Pre-deployment Security Audit (release-blocking, runs after Gate D, before the production push)

- 🟢 A **whole-system** security pass over the release candidate passes (secrets scan over the full tree · dependency vulnerability scan · input/boundary validation · authN/authZ · injection/output · error/log leakage · transport/storage · attack surface) with **0 unresolved CRITICAL/HIGH**, and **no deferred CRITICAL/HIGH security findings from any per-task Stage 4** remain open. Sign off in `delivery_log.md` (Gate S).
- 🔴 Shipping a release that is task-by-task clean but whole-system insecure — a secret baked into a build artifact, a newly exposed endpoint, a vulnerable transitive dependency, an auth gap at a module seam. Passing every Stage 4 does **not** imply this gate passes.
- 🛡 [security_gate.md](security_gate.md) (the single-home checklist + tooling) — distinct from the per-task Stage 4 `security-reviewer`.

## Gate (production) — Deployment

- 🟢 Production requires **`[RELEASE APPROVED]`** + a delivery verification number **that cites a passed Gate S**.
- 🔴 Approving a push without the security sign-off attached.
- 🛡 `deployment_log.md` + the approval-token gate.

## (Closing) — Review / Assetization

- 🟢 `lessons_learned.md` written **+ promotion to memory (MEMORY.md)** + cross-link.
- 🔴 Learning evaporates → the next project repeats the same trial and error (exactly what this kit aims to prevent).
- 🛡 The canonical `retrospective/lessons_learned.md`.

---

## At-a-Glance Summary — "When to Freeze What"

```
S0 Research   → 3 risks
S1 Initiating → scope + external-dependency boundaries
S2 Feasibility→ prove the core technology (spike/study)
S3 Planning   → ★ freeze the 3 contracts (data definition · output sink · identifier/unit) + WBS/DoD   ← this is the branch point for "the cost of going back to square one"
S4 Executing  → 6-stage gate per task
S6 Delivery   → Gate D (all green) → ★ Gate S (whole-system security audit) → [RELEASE APPROVED]
S7 Review     → lessons + memory promotion
```
