<!-- [Role] S1 Initiating-stage deliverable — the product/project charter scaffold.
     What this document decides: what/why/how-far to build + external-dependency boundaries.
     What this document does NOT decide: data definitions/storage structure/identifiers (= the 3 contracts of S3 Gate P) / implementation approach (= plan.md).
     How to fill it: replace {{...}} tokens with project values. Start empty and finalize on passing Gate I. -->

# Product Proposal / Charter — {{PROJECT_NAME}}

> **Version**: v0.1 (draft) · **Date**: {{YYYY-MM-DD}} · **Author**: {{ARCHITECT}}
> **Status**: ⚠ draft (Gate I not passed) — on finalization (Gate I pass), this document's authority level becomes `authoritative`.
> Macro process: [lifecycle-standard.md](lifecycle-standard.md) · Gate: [PHASE_GATES.md](PHASE_GATES.md) Gate I

---

## 1. Background · Problem Statement

<!-- What is the problem? Why build it now? One paragraph. -->
- {{PROBLEM_STATEMENT}}

## 2. Goals · Success Criteria (make them measurable)

| # | Goal | Success criterion (quantitative) |
|:--|:--|:--|
| G1 | {{GOAL_1}} | {{METRIC_1}} |
| G2 | {{GOAL_2}} | {{METRIC_2}} |

> ⚠ No vague goals like "works well" — only measurable criteria. (Basis: [STAGE_DEFINITION_RISKS.md](STAGE_DEFINITION_RISKS.md) S1)

## 3. Scope

| Category | Items |
|:--|:--|
| ✅ Included (in) | {{IN_SCOPE}} |
| ❌ Excluded (out) | {{OUT_OF_SCOPE}} |

> Scope boundaries have 🌍 global impact — if they wobble, the schedule/structure collapses. Nail them down at Gate I.

## 4. External-Dependency Boundary — 🌍 Important

<!-- HW / vendor API / subcontractor / external service. Building on an unfinalized dependency means a rewrite when it's finalized. -->
| Dependency | Finalized? | Boundary handling if unfinalized (stub/mock/facade) |
|:--|:--|:--|
| {{DEPENDENCY_1}} | unfinalized/finalized | {{BOUNDARY_HANDLING_1}} (e.g., only as far as stub/mock, defer work beyond that boundary) |

> Register unfinalized dependencies' paths in `.harness.toml [safety_boundary]` → no agent auto-modification.

## 5. Stakeholders

| Role | Owner | Engaged when |
|:--|:--|:--|
| Architect/Supervisor | {{ARCHITECT}} | All stages (decision-making) |
| {{STAKEHOLDER_ROLE}} | {{NAME}} | {{WHEN}} |

## 6. Milestone Overview (the detailed WBS is in plan.md)

| Milestone | Content | Notes |
|:--|:--|:--|
| {{MILESTONE_1_NAME}} | {{MILESTONE_1_DESC}} | |

## 7. Initial Risk Overview (details in research.md PART E)

| Risk | Impact | Initial response |
|:--|:--|:--|
| {{RISK_1}} | {{IMPACT_1}} | {{MITIGATION_1}} |

## 8. Approval (Gate I)

- [ ] Scope (in/out) finalized
- [ ] External-dependency boundaries stated
- [ ] Measurable success criteria agreed
- [ ] Architect approval: ____________  (switch to `status: authoritative`)

---

## Changelog

| Version | Date | Change |
|:--|:--|:--|
| v0.1 | {{YYYY-MM-DD}} | Initial draft (template baseline) |
