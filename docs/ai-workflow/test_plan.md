# [Phase 2+] Test Plan

<!-- ROLE BANNER: test design document (what to test, at which level, and when it must pass).
     What this document decides: test pyramid placement + per-Milestone coverage gates.
     What this document does NOT decide: the actual test code implementation (written in each task's RED step). -->

> This is a **design document**; the actual **test code** (`{{TESTS_ROOT}}/**/*.py`) is written by referencing this plan
> in each M-task's TDD loop (RED).
> First written: YYYY-MM-DD | Basis: `plan.md` §4 (WBS) / §6 (quality/test plan).

---

## 0. Purpose and Boundary of This Document

### 0.1 What This Document Decides
- **What** is tested — per-module list of target functions/boundaries/edge cases.
- **At which level** it is tested — L1~L5 pyramid placement.
- **When** it must pass — each M-task DoD + Milestone coverage gate.

### 0.2 What This Document Does Not Decide
- **The concrete implementation of the actual test code** — written in each task's RED step.
- **The exact byte sequence of mock data** — generated in `{{TESTS_ROOT}}/fixtures/*.py` from real observed values.

### 0.3 Plan ≠ Deployable Test Code (boundary principle)
- **The plan (this document)** = a **design** of "what to verify". **Not** a deployment target.
- **Test code** = actual runnable `pytest` files. **Not** a deployment target.
- The two are independent deliverables; the plan comes first, and the test code is actually implemented in each task.

---

## 1. Test Pyramid (L1 ~ L5)

| Level | Name | Target | Tools | Speed | Coverage Goal | Location |
|:----:|:-----|:-----|:-----|:----:|:-------------:|:-----|
| **L1** | Unit test | pure functions, computation logic | pytest | < 10ms | **80%+** (M-task DoD) | `{{TESTS_ROOT}}/unit/` |
| **L2** | Module/contract test | ABC implementations, schemas, DTOs | pytest + Protocol | < 100ms | 100% of all ABC methods | `{{TESTS_ROOT}}/unit/` → `contract/` (separation recommended) |
| **L3** | Integration test | module ↔ module (Router↔Service↔Core) | pytest + client | < 1s | 70%+ | `{{TESTS_ROOT}}/integration/` |
| **L4** | System test | all layers in a single process | pytest | < 10s | core flows | `{{TESTS_ROOT}}/integration/` |
| **L5** | E2E test | input → output golden path | pytest scenario | < 60s | golden path | `{{TESTS_ROOT}}/integration/test_e2e_*.py` |

**Boundary principles**:
- Unit (L1) has **no external dependencies** (file I/O, network, hardware all mocked).
- Contract (L2) verifies **only the ABC/Protocol/DTO interface**. Logic belongs to L1.
- Integration (L3) uses a **real framework client + fake adapters** — no real DB/hardware.
- System (L4) uses IPC for real, with external dependencies replaced by mocks.
- E2E (L5) is the full path — real input/output.

> **Pyramid vs compositional rings**: L1–L5 above are the *test-pyramid* (test type/scope by tooling). The compositional **Unit/Module/Integration rings** ([../_harness/compositional-verification.md](../_harness/compositional-verification.md)) are a *refinement, not an equivalence* — notably the **Module ring** tests the **real boundary** (emulator/device), which L3 "Integration (fake adapters)" deliberately mocks. See its §0 terminology bridge.

---

## 2. Milestone × Coverage Gate

| Milestone | New tests (est.) | Cumulative | Coverage Gate |
|:---------:|:---------------:|:----:|:-----------:|
| M1 | 00 | 00 | ≥80% (relevant module) |
| M2 | +00 | 00 | each task ≥80% |
| M3 | +00 | 00 | each task ≥80% |
| ... | +00 | 00 | overall ≥80%, integration ≥70%, E2E core flows |

> The coverage-gate numbers must match `.harness.toml [gates].coverage_threshold`.
> ⚠ `--cov` is measured by **dotted-module path** (no file path — prevents a false 0%).

---

## 3. Milestone × Level Matrix

| Milestone | L1 Unit | L2 Contract | L3 Integration | L4 System | L5 E2E |
|:---------:|:-------:|:-------:|:-------:|:--------:|:------:|
| **M1** | <module> | <contract> | — | — | — |
| **M2** | <module> | <contract> | — | — | — |
| **M3** | <module> | <contract> | <API/IPC> | <process> | — |
| **M_final** | <util> | <schema> | <integration> | <perf/security> | <e2e> |

---

## 4. Hardware/External Dependency Mocking Strategy

> Modules depending on the safety boundary (`.harness.toml [safety_boundary].paths`) are tested with mocks.
> Build the mock skeletons by copying `{{TESTS_ROOT}}/fixtures/_TEMPLATE_serial_mock.py` /
> `_TEMPLATE_driver_mock.py` (single source of truth for the protocol + fault/delay injection).
