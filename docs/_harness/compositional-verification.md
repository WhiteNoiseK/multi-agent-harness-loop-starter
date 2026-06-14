# Compositional Verification — Unit → Module → Integration; trusted-unit promotion after the Integration ring passes
#authority/system/active

> A stack-agnostic verification **ordering** discipline. For one feature it defines WHAT SCOPE of the system each
> test exercises (the three rings) and WHEN a verified feature becomes a reusable building block (trusted-unit
> promotion). It is **orthogonal** to the 6-stage scored loop ([quality-gates.md](quality-gates.md)), which defines
> the DEPTH of one increment (RED→GREEN→VERIFY→REVIEW→FIX→AUDIT). The two **nest**: the loop runs the **Unit ring**.

---

## 0. Terminology bridge (read first — prevents overload)

The **ring** names below are the **compositional axis** = *how much of the system a test exercises*. They are **NOT**:
- the pytest folders (`tests/unit`, `tests/integration`),
- the [test_plan.md](../ai-workflow/test_plan.md) **pyramid levels** L1–L5,
- the lifecycle **milestone** "M5 integration" ([lifecycle-standard.md](../pm-guide/lifecycle-standard.md)),
- **memory promotion** (lessons → `MEMORY.md`, lifecycle-standard §S7).

Ring ↔ pyramid is a **refinement, NOT an equivalence**:

| Ring | What it proves | ≈ pyramid | Key difference |
|:--|:--|:--|:--|
| **Unit** | isolated logic, Fakes, no real I/O | L1 + narrow L2 (contract; fakes/mocks) | — |
| **Module** | the **real boundary/seam** (DB/Auth/API/device) via emulator / sandbox / real-device / HIL / staging-safe adapter | (the pyramid mocks this at L3/L4) | the ladder **adds** a real-boundary ring the pyramid leaves mocked |
| **Integration** | the whole feature **E2E** across layers, **incl. negative paths** | L5-style E2E | only through **approved non-production / safe** boundaries |

> ⚠️ The kit's L3 "Integration (real framework client + **fake** adapters)" is a **logical** check — it is **NOT** the
> ladder's Module/Integration ring, which require **real** boundary evidence.

---

## 1. The three rings

| Ring | Definition | Where verified | Example |
|:--|:--|:--|:--|
| **Unit** | smallest logic in isolation — pure function, single class, upper logic with Fakes. No real I/O, fast, deterministic. | unit test runner (usually CI) | validator, ViewModel+Fake, mapper |
| **Module** | the component at its **real boundary** — adapters to real dependencies (DB/Auth/API/device/HW) exercised against an emulator / sandbox / real instance. Proves the **seam**, not the logic. | emulator / real-device / sandbox integration test | Repo ↔ emulator, API client ↔ mock server |
| **Integration** | the whole feature across layers, E2E (UI→logic→module→external). **Negative paths (blocked / denied / expired) included.** | E2E / scenario test | screen→VM→Repo→backend + unauthenticated block |

---

## 2. Safety-boundary caveat (Integration ring)

"Real I/O" means **approved non-production / safe** endpoints only — emulator, sandbox, staging. It must **NOT** touch
the production DB, real ads, real reward logic, or real location / identity verification until the relevant hard gate
approves it. Paths registered in `.harness.toml [safety_boundary].paths` stay **STUB in all rings**.

---

## 3. Trusted-unit promotion (distinct from memory promotion)

- A component becomes a **trusted unit** only **after its Integration ring passes**. Then it is treated as a
  **black-box building block** the next feature assembles on top of.
- **Trigger**: the Module and Integration rings run **separately** — a supervised device / emulator run, or a CI entry
  point. They are **not** automated by the 6-stage loop / [`/kit:harness-verify`](../../.claude/commands/kit/harness-verify.md).
  Record the run + result in `progress.md`.
- **Audit ownership**: trusted-unit promotion is an **architect-recorded gate** in `progress.md`. (`score-auditor` /
  Stage 6 covers only the Unit-ring loop; it does **not** certify promotion.)

> "Trusted-unit promotion" is the **compositional** event. It is **not** "memory promotion" (durable lessons →
> `MEMORY.md`), which lives in lifecycle-standard §S7 / the retrospective.

---

## 4. Loop integration (how the rings meet the 6-stage loop)

- The 6-stage / auto-harness loop **automates the Unit ring only** — its **Stage-3 VERIFY** runs **scoped unit tests**
  ([quality-gates.md](quality-gates.md) §Stage 3 is authoritative for what that scoped run executes).
- The **Module** and **Integration** rings run **outside** the loop (device / emulator, separately — §3 Trigger).
- `[HARNESS]` commit, `R4 CLOSE`, and "task close" mean **Unit-ring closure** — they do **NOT** mark the feature a
  trusted unit. Trusted-unit promotion happens later, after the Module + Integration rings pass.

---

## 5. Discipline (non-negotiable)

1. **Don't skip rings.** Logic verified at the Unit ring still needs its seam proven at the Module (real-boundary) ring.
2. **Don't grant trusted-unit promotion early.** Stacking larger things on a not-yet-integration-verified part accrues debt; allow it only as an explicit, time-boxed provisional step, and close the pending lower integration **before** final promotion.
3. **Close pending sub-integrations first** — a written-but-unrun module/integration test (waiting on a device/resource) must run before the part is treated as trusted.
4. **Cause isolation is the reward.** When every lower ring is verified, a new failure attributes exactly to the layer just added.

---

## 6. Checklist (any feature)

```
[ ] List the feature's layers (validator → adapter → ViewModel → screen → gate)
[ ] Unit: pure logic + Fakes → CI unit tests
[ ] Module: each real-boundary adapter against emulator / sandbox / real instance
[ ] Integration: whole feature E2E (incl. negative paths), approved safe boundaries only
[ ] Only AFTER Integration passes → record the "trusted unit" in progress.md; the next feature stacks on it as a black box
[ ] At promotion: no skipped ring / no unrun lower integration
```

---

## Cross-references

- [quality-gates.md](quality-gates.md) §Stage 3 — the scoped unit run **is** the Unit ring (authoritative for its mechanics); `[HARNESS]` commit = Unit-ring closure, not promotion.
- [test_plan.md](../ai-workflow/test_plan.md) — pyramid L1–L5 ↔ rings (refinement, not equivalence).
- [.claude/commands/kit/auto-harness.md](../../.claude/commands/kit/auto-harness.md) · [codex_loop_operating_policy.md](../ai-workflow/codex_loop_operating_policy.md) — `[HARNESS]` commit / R4 CLOSE = Unit-ring closure, not trusted-unit promotion.

## Change History

| Version | Date | Change | Decided by |
|:--|:--|:--|:--|
| v0.1 | 2026-06-14 | Initial — 3-ring ladder + terminology bridge (ring vs pyramid L-levels / M5 milestone / memory-promotion) + safety-boundary caveat + trusted-unit promotion (triggers + architect-recorded audit) + loop integration. Tri-engine reviewed (Claude / Codex / Gemini → SOUND). | architect |
