# TEMPLATE_MANIFEST — kit file inventory · roles · placeholder checklist

> **What every file in this kit is for**, at a glance. Each file defines only its *role*; the
> project content is empty (an empty template). Places to fill are marked with `{{PLACEHOLDER}}`.
> ✅ = a script reads `.harness.toml` **at runtime** and applies it (defaults if unset) — `harness_init.py` writes/manages `.harness.toml`.
> 🖊 = a placeholder a human fills in directly (product name, goals, deployment URL, etc.).

Status legend: **AS-IS** use as-is · **PARAM** placeholder substitution needed · **EMPTY** an empty skeleton with only its role defined · **OPT** optional (per language/target)

---

## A. Kit Root · Config

| File | Role | Status |
|:--|:--|:--|
| `README.md` | Kit entry point — clone-and-go procedure, the 3 problems, folder map | PARAM 🖊 |
| `START_HERE.md` | **Agent activation manual** — kickoff prompt + AI activation runbook (for both humans and agents) | AS-IS |
| `.mcp.json.example` | Shared team MCP config template (copy → .mcp.json, `${ENV}` expansion) | PARAM 🖊 |
| `TEMPLATE_MANIFEST.md` | This document — file inventory + global prerequisites | AS-IS |
| `.harness.toml` | **The single config seam** — paths, thresholds, task-id, language, safety boundaries. Read by every script | PARAM ✅ |
| `pyproject.toml` | **Single home for tool config** — `[tool.mypy/ruff/black/coverage/pytest]`. The original project lacked this, so config was scattered across scripts | PARAM ✅ |
| `requirements.txt` | Production dependencies (single canonical copy — removes the original project's root/backend duplication) | PARAM 🖊 |
| `requirements-dev.txt` | Harness toolchain: pytest+asyncio+cov+mock+timeout+mypy+ruff+black+bandit | AS-IS |
| `.gitignore` | Ignore caches, builds, node_modules, scores runtime artifacts (scratch via wildcard) | AS-IS |
| `.env.example` | Secret/config bootstrap stub (no-hardcoding principle) | EMPTY 🖊 |
| `.clauderules` | Canonical language-agnostic code-quality rules (50/800 SLOC · nesting ≤3 · immutability · TDD-DoD · rollback) | AS-IS |

## B. Macro Process (`docs/pm-guide/`)

| File | Role | Status |
|:--|:--|:--|
| `lifecycle-standard.md` | **Standard lifecycle** — PMBOK + Research + Feasibility, 8 stages. The spine of the macro process | AS-IS |
| `PHASE_GATES.md` | **8-gate one-page checklist** — per gate [frozen deliverables / risk if missed / mitigation]. Gate P (3-contract freeze) is central | AS-IS |
| `STAGE_DEFINITION_RISKS.md` | **Per-stage what-to-define · blast radius · risk-if-undefined (examples) · standard names (V-model/12207/Data Dictionary/ICD)** | AS-IS |
| `DRIFT_LOCK.md` | **The 22-kind drift lock list** — the answer key for "what drifts" + the baseline-diff ritual | AS-IS |
| `recommendation_policy.md` | **Recommendation & auto-verification policy** — 4-column scorecard (stability/maintainability/visibility/security) + the 6 stages auto-run when code changes | AS-IS |
| `security_gate.md` | **Gate S — Pre-deployment Security Audit** — release-blocking whole-system security checklist (separate from per-task Stage 4) | AS-IS |
| `ProductProposal.md` | Initiating-stage charter scaffold | EMPTY 🖊 |

## C. 6-Stage Gate Engine (`docs/_harness/` · `.claude/` · `scripts/`)

| File | Role | Status |
|:--|:--|:--|
| `docs/_harness/quality-gates.md` | **Vendored** 6-stage spec (thresholds, permission matrix, JSON schema, isolation_header). Self-contained | PARAM |
| `docs/_harness/TASK_ID_GRAMMAR.md` | Canonical task-id grammar — imported by the commit guard (prevents silent no-op) | AS-IS |
| `.claude/settings.json` | **Only the hooks{} block** (PreToolUse→harness_gate_check.sh) + empty `allow:[]` | PARAM ✅ |
| `.claude/agents/test-writer.md` | Stage 1 RED — writes tests/ only, must not read src/ (blocks reverse bias) | PARAM ✅ |
| `.claude/agents/impl-coder.md` | Stage 2 GREEN — writes src/ only, tests/ read-only | PARAM ✅ |
| `.claude/agents/refactor-fixer.md` | Stage 5 FIX — fixes only within the findings scope | AS-IS |
| `.claude/agents/score-auditor.md` | Stage 6 AUDIT — re-runs and cross-checks the claimed numbers | PARAM ✅ |
| `.claude/commands/kit/harness-verify.md` | Stage 3→6 orchestration + **the single source for the stage→agent mapping** | PARAM ✅ |
| `scripts/harness_init.py` | **Bootstrap** — create/update .harness.toml + snapshot .harness/baseline + check hooks/prereqs, then fail loudly (no token substitution — scripts read at runtime) | AS-IS |
| `scripts/_harness_config.py` | Shared runtime config loader — reads .harness.toml and merges defaults if absent (single source for all scripts) | AS-IS |
| `scripts/harness_gate_check.sh` | PreToolUse hook shim (→ harness_audit_rerun.py) | AS-IS |
| `scripts/harness_run_verify.sh` | Stage 3 VERIFY (Layer A). **The --cov dotted-module bug fix** + SELFTEST lock | PARAM ✅ |
| `scripts/harness_audit_rerun.py` | Layer C commit guard — on a [HARNESS] commit, re-run and cross-check pytest/mypy/ruff/cov. **Generalized to multi-segment task-ids** | PARAM ✅ |
| `scripts/harness_status.sh` | Session-recovery diagnostics (progress + git + pytest) | PARAM ✅ |

## D. Foam Knowledge Base (`docs/` root · `scripts/`)

| File | Role | Status |
|:--|:--|:--|
| `docs/index.md` | MOC — the starting point when you lose context (3 catalog links + domain router) | PARAM 🖊 |
| `docs/_knowledge-architecture.md` | **Format SSOT** — file naming/meta-block/wikilink/trust-model/MOC conventions. Core of the methodology | AS-IS |
| `docs/_recent.md` | Most-recent-first catalog (auto-generated) — **same empty stub as the zero-doc output** | EMPTY |
| `docs/_authority.md` | Authority registry (auto-generated, §8 parsing) | EMPTY |
| `docs/_field_cascade.md` | Field→document dependency map (auto when a spec appears) | EMPTY |
| `scripts/foam_catalog.py` | `_recent`/`_authority` generator (parses CLAUDE.md §8) | AS-IS |
| `scripts/field_cascade.py` | `_field_cascade` generator — **auto-discovers spec paths** (removes the original project's hardcoding) | PARAM |
| `mkdocs.yml` + `scripts/build_docs_portal.py` | **Human-review docs portal** — renders `docs/` md → searchable HTML (Material theme, auto-nav). md stays SSOT; `site/` gitignored | AS-IS |
| `docs/PORTAL_README.md` · `requirements-docs.txt` · `docs/.pages` | Portal usage/limits · portal-only deps (not runtime) · auto-nav top ordering | AS-IS |

## E. Empty Phase-Deliverable Templates (`docs/ai-workflow/`)

| File | Role (Phase) | Status |
|:--|:--|:--|
| `research.md` | Phase 1 research/risks — PART A–F skeleton. **Analysis/history only** (no contract storage) | EMPTY |
| `plan.md` | Phase 2 plan — WBS + per-task DoD + verification commands + functional-spec table | EMPTY |
| `progress.md` | M&C ledger — authority table/current state/active·next/blockers. **First read on cold restart** | EMPTY |
| `implementation_log.md` | Phase 3 daily log (done/issues/decisions/next) | EMPTY |
| `decision_pending.md` | Architect decision queue (legend + intake protocol) | EMPTY |
| `terminology.md` | Glossary (canonical/legacy mapping/confusion check) | EMPTY |
| `test_plan.md` | L1–L5 test pyramid + the "plan ≠ shipped test code" boundary | EMPTY |
| `research_temp.md` | Staging log for research.md changes | EMPTY |
| `delivery_log.md` | Phase 4 QA/staging (Monkey test) | AS-IS |
| `deployment_log.md` | Phase 5 deployment — `[RELEASE APPROVED]` gate | AS-IS |
| `codex_claude_review_protocol.md` | **Multi-agent collaboration governance** — Single Writer/Independent Reviewer (e.g. Claude↔Codex) · R0–R4 · PROMPT-ID convention · handoff/Pass-Block (AGENTS.md §11 links here, activated via `.harness.toml [review_overlay]`) | PARAM |
| `ecc-harness-guide.md` | Phase→agent/skill mapping + DoD checklist | PARAM |
| `scores/README.md` · `reviews/README.md` · `handoffs/README.md` | Directory naming/schema conventions. The directories stay empty | AS-IS |
| `scores/EXAMPLE_full_lifecycle.json` | One schema-teaching example (0 real task JSON) | AS-IS |
| `tasks/<TASK-ID>_plan.md` | Per-task trio template (demonstrates the header block) | EMPTY |

## F. FREEZE-Gate Contract Templates (`docs/engineering/` · `docs/experiments/`)

> **The deliverables Gate P requires you to fill at v1.0.** If these are empty, do not enter Executing.

| File | Role | Status |
|:--|:--|:--|
| `_TEMPLATE_data_spec.md` | **Data-definition contract** — columns·formulas·units·ranges·DB mapping + §3.1 ```text header (for field_cascade) + Changelog | EMPTY |
| `_TEMPLATE_erd.md` | **Output-sink contract** — tables + the Object-Identifier↔PK Mapper doctrine | EMPTY |
| `_TEMPLATE_identifier_unit_contract.md` | **Identifier/unit contract** — layered authority (internal ID/external ID/Mapper) + anchor constants (ts unit · id base) | EMPTY |
| `_TEMPLATE_assumption_leak_audit.md` | Planning→Executing legacy-leak audit (**required when cloning**) | EMPTY |
| `_TEMPLATE_engineering_sim.md` | Engineering simulation report | EMPTY |
| `_TEMPLATE_trade_study.md` | Technology/algorithm trade study | EMPTY |
| `experiments/_TEMPLATE_spike_report.md` | **Feasibility spike** — purpose/criteria/environment/method+result/hypothesis matrix/operational impact/vendor questions/conclusion | EMPTY |

## G. Conventions · Tests · CI

| File | Role | Status |
|:--|:--|:--|
| `docs/coding-convention/README.md` · `Python.md` | Conventions (Python always) | AS-IS / PARAM |
| `docs/coding-convention/JavaScript.md` · `C.md` | Web/firmware (optional) | OPT |
| `docs/coding-target/webCodingProtocol.md` · `firmwareCodingProtocol.md` | Per-target protocols (optional) | OPT |
| `docs/retrospective/lessons_learned.md` | Phase 6 retrospective (**single canonical copy** — no ai-workflow duplicate shipped) | AS-IS |
| `tests/{unit,integration,e2e}/__init__.py` | Test layout | AS-IS |
| `tests/conftest.py` | Reusable fixtures only (env isolation + async teardown + TYPE_CHECKING guard) | PARAM |
| `tests/integration/conftest.py` | autouse env-guard example | PARAM |
| `tests/fixtures/_TEMPLATE_serial_mock.py` | Serial-device mock skeleton (device-API + test-control-API separated, protocol truth in a single source) | EMPTY |
| `tests/fixtures/_TEMPLATE_driver_mock.py` | Driver/register mock skeleton (fault/delay injection, deterministic) | EMPTY |
| `tests/test_harness_hardening.py` | **Harness self-test** — gate behavior · forgery rejection · timeout · existence of script paths cited in the spec. Running it once after cloning = an acceptance test | PARAM |
| `pytest.ini` | Consolidated into pyproject.toml `[tool.pytest.ini_options]` — not shipped | — |
| `.github/workflows/harness.yml` | CI — the same gates as the local hooks | PARAM 🖊 |
| `.harness/baseline/` | Snapshot at clone time (the drift-diff reference) | generated (init) |

## H. AI Collaboration Tools · Environment (`docs/ai-tooling/` · `docs/`)

| File | Role | Status |
|:--|:--|:--|
| `START_HERE.md` (root) | Agent activation manual + kickoff prompt (for both humans and agents) | AS-IS |
| `docs/ai-tooling/AI_TOOLING.md` | Definition of needed agents · commands · skills · MCP + verification/install (ECC · configure-ecc · claude mcp add) | AS-IS |
| `docs/ENVIRONMENTS.md` | Per-environment (IDE/terminal/app) optimization + settings scope | AS-IS |
| `.mcp.json.example` (root) | Committable MCP config template (per-purpose verification table + `${ENV}`) | PARAM 🖊 |

## I. Codex Auto-Collaboration Loop (the "loop" layer — headless Claude↔Codex)

> The differentiator of this kit over the base starter kit. Single Writer = Claude / Independent Reviewer =
> Codex, driven headlessly with **zero human copy-paste**. Activated via `.harness.toml [review_overlay].enabled = true`.
> Logic layer (Codex review) **AND** fact layer (local re-run, `claimed == actual`) must both pass.

| File | Role | Status |
|:--|:--|:--|
| `.claude/commands/kit/auto-harness.md` | **The loop command** — `/kit:auto-harness` runs the R0–R4 Claude↔Codex round-trip via `codex exec` until the current stage closes. Encodes the stage loop + gate policy | AS-IS |
| `docs/ai-workflow/codex_automation_setup_guide.md` | **Headless bridge how-to** — install/auth/session-resume/verdict-capture for `codex exec` (read-only sandbox, file-route UTF-8, hash manifest). Project-agnostic (`<...>` placeholders) | AS-IS |
| `docs/ai-workflow/codex_loop_operating_policy.md` | **Operating policy** — auto-proceed model (severity is NOT a stop axis), the 5 STOP triggers, two-layer gate, PROMPT-ID/handoff conventions, the 5 priorities | AS-IS |
| `scripts/auto_gate.py` | **Decision engine** — given reviewer-JSON + local-verify + changed paths, decides auto_continue vs stop. Boundary patterns config-driven via `.harness.toml [safety_boundary]` | PARAM ✅ |
| `scripts/run_codex_review_bridge.py` | **Bridge transport + hygiene** — write_request / run_codex_review (injectable `codex_exec`) / archive / `assert_payload_clean` (blocks secrets·SQL·db-paths·tracebacks leaving for the reviewer) | AS-IS |
| `.codex/agents/{test-writer,impl-coder,refactor-fixer,score-auditor}.toml` | **Codex-side role agents** — mirror the `.claude/agents/` 6-stage roles for the independent reviewer | PARAM |
| `.codex/hooks.json` | Codex PreToolUse hook → `scripts/harness_gate_check.sh` (same gate as the Claude side) | AS-IS |
| `.harness.toml [review_overlay]` / `[integrity]` | Loop config — `enabled` · `severity_auto_max` · `fact_layer_required` · `stop_points_acknowledged` (first-run consent gate; operator owns the unchanged thresholds) + the review hash manifest (reviewer no-edit detection) | PARAM ✅ |
| `.claude/commands/kit/recommend.md` | **`/kit:recommend [focus]`** — **tri-engine** (Claude + Codex + Antigravity) recommendation under the 4-column policy (stability/security/maintainability/visibility + no temp fix); a trailing arg weights one axis. General-purpose (bundled with the loop edition, not loop-specific) | AS-IS |
| `.claude/commands/kit/resume-break.md` | **`/kit:resume-break [hint]`** — analyze the break point + fact-layer check (claimed==actual) + safe resume from the unfinished stage only. General-purpose | AS-IS |
| `.claude/commands/kit/checkpoint.md` | **`/kit:checkpoint [hint]`** — the write-side complement of `/kit:resume-break`: record a clean break point (progress.md break block · scores · resume-prompt · memory) after a fact-layer check, so a fresh session resumes with zero loss / zero duplicate work. General-purpose | AS-IS |

> **Command namespace.** All five bundled commands live under `.claude/commands/kit/`, so they group under one
> typeable prefix — type `/kit` and `/kit:harness-verify · /kit:auto-harness · /kit:recommend · /kit:resume-break · /kit:checkpoint`
> appear together (and never collide with global/ECC commands).
| `tests/unit/test_auto_gate.py` · `test_codex_review_bridge.py` | Tests for the two loop scripts (123 + 46) — bundled so the loop layer ships verified | AS-IS |

---

## Global Prerequisites — without these, the harness silently goes inert

`harness_init.py` checks for their existence and, if missing, **fails loudly**.

| Prerequisite | Location | If missing |
|:--|:--|:--|
| `quality-gates.md` | **Vendored** into `docs/_harness/` (self-contained) — the global copy is optional | Loses the threshold/schema source |
| `code-reviewer` agent | `~/.claude/agents/` (global) | Stage 4 REVIEW impossible |
| `security-reviewer` agent | `~/.claude/agents/` (global) — **must be trimmed to read-only** (the original project's copy held Write permission = a matrix violation) | Stage 4 security review impossible |
| `planner` · `architect` | `~/.claude/agents/` (global) | Loses Phase 1–2 assistance |
| `/harness-audit` · `/quality-gate` | `~/.claude/commands/` (global) | Loses the drift-check tooling |

> The Stage 1/2/5/6 agents (test-writer · impl-coder · refactor-fixer · score-auditor) are **bundled in this kit** —
> they are the highest-value, lowest-drift assets, so they are vendored. Only the Stage 4 reviewers depend on the global layer.
