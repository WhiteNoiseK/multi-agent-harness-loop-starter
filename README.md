# Claude × Codex × Gemini Multi-Agent Harness Loop Starter

> **Claude builds. Codex reviews. Gemini documents. The gate re-runs everything — hallucinated results don't survive.**

[![License: MIT](https://img.shields.io/github/license/WhiteNoiseK/claude-codex-harness-loop-starter)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/WhiteNoiseK/claude-codex-harness-loop-starter?style=social)](https://github.com/WhiteNoiseK/claude-codex-harness-loop-starter/stargazers)
![Built for Claude Code](https://img.shields.io/badge/built%20for-Claude%20Code-8A2BE2)
![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

A **clone-and-go** starter kit for a **three-engine autonomous engineering loop**: Claude implements (Single Writer),
Codex independently reviews (Independent Reviewer), and Gemini generates docs/wikis headlessly — all without
human copy-paste. On top of a proven 6-stage quality gate, a Foam knowledge base, and drift-locking, all in place
**from day one**.

| Agent | Role | How |
|:--|:--|:--|
| **Claude** | Single Writer — implements, self-reviews (6-stage gate) | in-session via Agent tool |
| **Codex** | Independent Reviewer — R0–R4 logic review | headless `codex exec` |
| **Gemini** | Doc/Wiki Generator — Foam entries, research drafts, changelogs | headless `gemini -p` |

### Why it's different

- 🔒 **Hallucination-proof gate** — every claimed pass count / coverage / type-check is **re-executed locally
  and diffed** (`claimed == actual`). Fabricated numbers die at the AUDIT stage *and* again at the commit guard.
- 🧩 **Claude uses zero headless commands** — the full 6-stage build runs **in-session** via the Agent tool;
  only the reviewer (Codex) and doc-generator (Gemini) run headless. **The loop keeps building even where `claude -p` is unavailable.**
- ♾️ **Runs until a real problem** — findings self-heal in the FIX loop (severity is *not* a stop axis); it halts
  only on 5 real triggers (trust-collapse · 3× retry · safety-boundary · judgmental · spec-conflict).
- 📝 **Gemini for docs, Codex for code** — role separation is strict: Gemini never touches code review, Codex never generates docs. Each engine stays in its lane.

```text
  Single Writer (Claude, in-session)            Independent Reviewer (Codex, headless)
           |                                                    |
  RED -> GREEN -> VERIFY -> REVIEW -> FIX -> AUDIT  --handoff-->  R0 ... R4 review
           |                                                    |
           v                                                    v
    FACT layer: local re-run              AND          LOGIC layer: reasoned review
    (claimed == actual?)                                  (PASS / BLOCKED)
           +------------------- both pass? ---------------------+
                       |
             yes -> [HARNESS] commit     |     no -> FIX self-heals, or STOP on 1 of 5 axes
```

## Quick start

```bash
# tracked-only export into a new project (no .git / caches dragged along)
git clone --depth 1 https://github.com/WhiteNoiseK/claude-codex-harness-loop-starter my-project
cd my-project && rm -rf .git && python scripts/harness_init.py    # harness_init is optional
```

Then, in **Claude Code**: turn on `.harness.toml [review_overlay]`, wire the headless reviewer
([setup guide](docs/ai-workflow/codex_automation_setup_guide.md)), and run **`/kit:auto-harness`**.
Full procedure → [§1](#1-how-to-start-a-new-project-clone-and-go) · all `/kit:` commands → [§4](#4-the-codex-auto-collaboration-loop-this-kits-addition).

This kit was extracted from a **real instrumentation-software project** from which this methodology emerged.
That project was both the most exemplary case of this methodology — and at the same time the one that most
clearly showed *what was left until too late and had to be revisited*. The kit captures both:
**what worked becomes the defaults**, and **what hurt to learn becomes gates and locks**.

---

## 0. The 3 Problems This Kit Solves

| # | Problem (actually experienced on the original project) | The kit's solution |
|:--|:--|:--|
| 1 | **Contracts frozen later than the code** → "feeling like going back to square one" (starting M1 with formulas undecided, then switching CSV→DB) | **Gate P (3-contract freeze gate)** — freeze the data-definition, output-sink, and identifier/unit contracts before the pipeline begins, or isolate them behind a facade |
| 2 | **The standard process living only as tacit knowledge** → trial and error repeated every time | **`docs/pm-guide/lifecycle-standard.md` + `PHASE_GATES.md`** — an explicit 8-stage gate model (PMBOK + Research + Feasibility) |
| 3 | **"Something drifts a little every time I start, but I can't tell what"** | **`docs/pm-guide/DRIFT_LOCK.md` + `.harness.toml` + `.harness/baseline/`** — identify and pin down 22 kinds of drift, and after cloning use a baseline diff to make "exactly what changed" visible |

---

## 1. How to Start a New Project (clone-and-go)

> 🚀 **The fastest path — one sentence to your agent**: copy the kickoff prompt from [START_HERE.md](START_HERE.md)
> and tell the agent "apply this kit to my project," and it will follow the activation runbook as written. The manual procedure follows below.

```
1. Export the kit's TRACKED files only into the new project (no .git / caches / site/ / .coverage):
     mkdir my-new-project && git -C harness-starter-kit archive HEAD | tar -x -C my-new-project
     (or: git clone --depth 1 <kit-url> my-new-project && rm -rf my-new-project/.git)
     Avoid `cp -r` — it drags in .git, __pycache__/, site/, .coverage and other local artifacts.
2. python scripts/harness_init.py                   ← the single bootstrap (a nice-to-have settling step; nothing breaks without it)
     - Enter SRC_ROOT / TESTS_ROOT / SCORES_DIR / TASK_ID_REGEX / coverage & audit thresholds → creates/updates .harness.toml
     - Snapshot .harness/baseline/ (the drift-diff reference)
     - Confirm the PreToolUse commit-guard hook is registered + verify global prereqs exist → fail loudly if missing
   * The scripts read .harness.toml **at runtime** and fall back to sensible defaults when it is absent —
     so init is not a single point of failure (stability-first principle). Only the paths in pyproject.toml are read
     statically by the tools, so if your layout is not src/tests, edit pyproject.toml directly.
3. Work through the "placeholders to fill in" checklist in TEMPLATE_MANIFEST.md
4. Read docs/pm-guide/lifecycle-standard.md and start from Stage 0 (Research)
```

> Even before the bootstrap, the scripts work with sensible defaults (so init never becomes a single point of failure).

## 2. When You Lose Context (cold restart)

Type `context check` and the agent reads in a fixed order and gives a 3–5 line summary:
`docs/index.md → _recent.md → _authority.md → _field_cascade.md → ai-workflow/progress.md → git status`.
This Foam wiring is the "start gate" — as the content fills in, the catalogs are generated automatically
(`python scripts/foam_catalog.py`).

## 3. Folder Map

For the full file list, roles, and placeholders to fill, see **[TEMPLATE_MANIFEST.md](TEMPLATE_MANIFEST.md)**.

```
harness-starter-kit/
├── README.md                  ← this document
├── START_HERE.md              ← 🚀 agent activation manual + kickoff prompt (for both humans and agents)
├── TEMPLATE_MANIFEST.md       ← full file inventory + roles + placeholder checklist + global prereqs
├── .mcp.json.example          ← shared team MCP config template (copy → .mcp.json)
├── .harness.toml              ← the single config seam (read by every script/agent — the core of drift locking)
├── pyproject.toml             ← single home for tool config ([tool.mypy/ruff/black/coverage/pytest])
├── docs/
│   ├── pm-guide/              ← macro process + behavior/policy layer
│   │                            (lifecycle-standard · PHASE_GATES · STAGE_DEFINITION_RISKS · DRIFT_LOCK · recommendation_policy · ProductProposal)
│   ├── _harness/             ← 6-stage gate spec (vendored, self-contained)
│   ├── ai-workflow/          ← empty Phase-deliverable templates (research/plan/progress/...) + scores/reviews/handoffs
│   ├── engineering/          ← FREEZE-gate contract templates (_TEMPLATE_data_spec / _erd / _identifier_unit_contract / _assumption_leak_audit)
│   ├── experiments/          ← Feasibility spike report template
│   ├── coding-convention/    ← per-language conventions (Python always, JS/C optional)
│   ├── ai-tooling/           ← AI_TOOLING.md (agents · commands · skills · MCP predefinitions · installation)
│   ├── ENVIRONMENTS.md       ← per-environment (IDE/terminal/app) optimization + settings scope
│   └── retrospective/        ← Phase 6 retrospective (single canonical copy)
├── .claude/                   ← harness agents (test-writer/impl-coder/refactor-fixer/score-auditor) + commands/kit/ (→ /kit:harness-verify · /kit:auto-harness · /kit:recommend · /kit:resume-break) + settings (hooks only)
├── .codex/                    ← Codex-side role agents (mirror .claude/agents) + hooks — the loop's independent-reviewer side
├── scripts/                   ← harness_init · gate_check · run_verify · audit_rerun · status · foam_catalog · field_cascade · auto_gate · run_codex_review_bridge
├── tests/                     ← unit/integration/e2e layout + reusable fixtures + hardware mock templates + harness self-test
├── .github/workflows/         ← CI (the same gates as the local hooks)
└── .harness/baseline/         ← snapshot taken at clone time (the drift-diff reference)
```

## 4. The Multi-Agent Collaboration Loop (this kit's addition)

The differentiator over the base starter kit: a **three-engine headless loop** with zero human copy-paste.

### 4a. Claude ↔ Codex: Code Review Loop

- **Roles**: Single Writer = Claude (designs / implements / self-reviews) · Independent Reviewer = Codex (R0–R4).
- **How**: `/kit:auto-harness` drives the round-trip via `codex exec` (read-only sandbox). Setup: [docs/ai-workflow/codex_automation_setup_guide.md](docs/ai-workflow/codex_automation_setup_guide.md).
- **Gate**: the Codex logic review **AND** a local re-run fact layer (`claimed == actual`) must both pass — a reviewer PASS alone is never sufficient.
- **Policy** ([codex_loop_operating_policy.md](docs/ai-workflow/codex_loop_operating_policy.md)): severity is **not** a stop axis (findings self-heal in the 6-stage FIX loop); user-stop only on 5 axes — trust-collapse · retry-exhaustion (3×) · safety-boundary · judgmental decision · spec/authority conflict. A high-stakes project may *opt in* to a severity gate (`severity_is_stop_axis = true` in `.harness.toml`, threshold `severity_auto_max`); the default is off.
- **Activate**: set `enabled = true` in `.harness.toml [review_overlay]`. Decision engine = `scripts/auto_gate.py`; transport = `scripts/run_codex_review_bridge.py`.
- **First run (consent gate)**: before the loop runs for the first time, the agent presents the stop-points and asks you to approve them as-is (`stop_points_acknowledged`). Thereafter the thresholds are your responsibility ([policy §0](docs/ai-workflow/codex_loop_operating_policy.md)).

### 4b. Claude → Gemini: Document Generation

- **Role**: Gemini = headless doc/wiki generator. **Not a code reviewer** — role is strictly document generation.
- **Use cases**: Foam knowledge-base entries, `research.md` drafts from raw notes, changelogs, release notes, any task where Gemini's large context window is preferred.
- **How**: Claude builds a generation prompt → sends headless via `gemini -p` → captures output → integrates as first draft. Setup: [docs/ai-workflow/gemini_automation_setup_guide.md](docs/ai-workflow/gemini_automation_setup_guide.md).
- **Claude is always the final integrator**: Gemini output = first draft only. Claude verifies against single-authority specs before committing.
- **Config**: `.harness.toml [review_overlay]` has a NOTE that Gemini is not listed as a reviewer — intentional.

### 4c. `/kit:recommend` — Dual-Engine Decision Scorecard

Every `/kit:recommend` call **always** runs both engines (no flag needed):
1. Claude scores independently on 4 axes (stability · security · maintainability · visibility).
2. Claude sends handoff to Codex → Codex scores independently.
3. Synthesize: agreement = high-confidence pick · disagreement = show both scorecards side by side and escalate if stability/safety axes diverge.

Full file list: **TEMPLATE_MANIFEST.md §I**.

## 5. Global Prerequisites

This kit is half of a system. The other half (the 6-stage thresholds, the permission matrix, some review agents)
depends on the `~/.claude/` global layer. We secured self-containment by **vendoring `docs/_harness/quality-gates.md`**,
but the Stage 4 reviewers (code-reviewer · security-reviewer) and planner/architect are
still global agents. For the exact list of prerequisites and an existence check, see **TEMPLATE_MANIFEST.md §Global Prerequisites**.

## 6. License & Credits

- **License**: [MIT](LICENSE) — © 2026 WhiteNoiseK. Use, modify, and distribute freely (just keep the copyright notice).
- **Methodology — VHCP**: a **development methodology defined by WhiteNoiseK** (fusing PMBOK-based project management + SW Agile + the characteristics of working with AI). The 8-stage lifecycle in this kit is an extension of VHCP.
- **Code**: generated with Claude (Anthropic) (AI-assisted). Designed assuming a **Claude Code** environment.
- **Recommended companion — ECC (Everything Claude Code)**: by Affaan Mustafa, MIT license. This kit does **not bundle** ECC; it only points to the install path ([docs/ai-tooling/AI_TOOLING.md](docs/ai-tooling/AI_TOOLING.md)). Using them together reinforces your global agents/skills.
- **Reference standards**: PMBOK (PMI), V-model, ISO/IEC/IEEE 12207 — only the names and process groups are referenced (the source texts are not included).
- This kit was extracted and validated from one real instrumentation-software project, and all product-identifying information has been replaced with neutral examples.
