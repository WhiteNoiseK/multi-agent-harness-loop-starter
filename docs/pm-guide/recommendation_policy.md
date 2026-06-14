# Recommendation & Auto-Verification Policy

> The policy an AI agent must follow **when proposing options or modifying code**. One of the behavioral layers that
> raised the output quality of the original project — "how to propose, and how an adopted proposal goes all the way to verification."
> Code-quality rules are in [.clauderules](../../.clauderules); the macro process is in [lifecycle-standard.md](lifecycle-standard.md).

---

## 1. Recommendation (Proposal) Rules — A 4-Column Evaluation Table Is Required

When presenting options/approaches, you **must** present them as an evaluation table on the 4 criteria below.
**Do not use intuitive/subjective phrasing alone** — like "more natural flow" or "cleaner" — use only axes with evidence.

| Criterion | What it looks at |
|:--|:--|
| **Stability** | Error likelihood, risk of data loss/race conditions, recoverability. In a hard-to-access/high-availability environment, **weighted highest**. |
| **Maintainability** | Ease of change, coupling/cohesion, testability, single-source compliance. |
| **Visibility** | Can a non-specialist (mechanical/electrical/field QA/subcontractor) read it? Flat structure, sufficient comments/docstrings. |
| **Security** | Attack surface, input-validation/boundary handling, secret/credential exposure, injection & authN/authZ risk. Even for a proposal, weigh whether it widens the attack surface or leaks data. |

Example format:

| Option | Stability | Maintainability | Visibility | Security | Notes |
|:--|:--|:--|:--|:--|:--|
| A. … | High — failure paths isolated | Medium — 1 module | High — guard clause | High — no new surface | Recommended |
| B. … | Medium | High | Medium | Medium — adds an endpoint | |

> Default priority: **stability > recoverability > security > visibility > maintainability > performance** (adjust per project NFR in `.harness.toml` or the charter — e.g. security rises toward the top for networked/multi-user/data-sensitive systems).
> The **release-blocking** counterpart of the Security axis is [Gate S — Pre-deployment Security Audit](security_gate.md).

## 2. Authority-Bound Values Are Not Options — priority **and** single

An **authority-bound** value is **to be complied with**, never offered as a proposal/option. Two cases:
- **Priority authority (우선권위 — the default early in a project)**: a binding quantitative (performance/function) target still living *inside a derived working doc* (plan/progress/research) **before** it is frozen into a spec at Gate P. Comply with it, even though its host file is non-authoritative.
- **Single authority (post-Gate-P)**: a value *defined* by a frozen single-authoritative spec (e.g., angle range, unit, identifier convention). If the code differs from the spec = the code is wrong.

Question/propose **only the open items (process/wiring/spec refinement)** — never an authority-bound value.
(Basis: priority authority [_knowledge-architecture.md §2](../_knowledge-architecture.md) · single authority §8 · [STAGE_DEFINITION_RISKS.md](STAGE_DEFINITION_RISKS.md) Gate P.)

## 3. If Code Modification Is Involved = Run the 6 Stages Automatically

If a proposal **involves modifying code**, then on adoption carry the following through *automatically* to the end (no skipping stages):

```
REVIEW (code + security in parallel) → FIX (findings scope) → AUDIT (re-run comparison)  → commit [HARNESS]
```

- If there is a "proceed as recommended"–type approval, proceed **automatically all the way to commit without per-stage explicit user approval**.
- However, **safety boundaries** (`.harness.toml [safety_boundary]`: DB migration / hardware driver / external device / shutdown, etc.) are excluded from auto-proceeding — explicit user approval is required.
- 6-stage details · thresholds: [_harness/quality-gates.md](../_harness/quality-gates.md).

## 4. No Stopgaps

Discard what's wrong immediately + correct it in one sweep with a new structure. A deprecated gradual migration = two systems coexisting +
higher future correction cost. (The only exception is a deprecation notice for an external API.)

---

## 5. Sources

- Codifies the user's global memory `feedback_recommendation_review_criteria` / `feedback_auto_recommendation_review` /
  `feedback_spec_authority_not_a_choice` / `feedback_no_temporary_fix` as project policy.
- This policy is included in the kit as part of the behavioral layer (below):
  `.claude/CLAUDE.md` (collaboration protocol) · `.clauderules` (code quality) · `docs/coding-convention/*` (per-language) ·
  `docs/pm-guide/*` (macro process) · **this document** (proposal/verification policy).
