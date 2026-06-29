# Changelog

Notable changes to the multi-agent-harness-loop-starter kit. Dates are ISO (`YYYY-MM-DD`).

## 2026-06-29

### Fixed — headless Antigravity (`agy`) was unreliable on Windows ("agy never responds")

**What was the problem.** Driving Antigravity headless with `agy -p "<prompt>"` appeared to do nothing —
the command exited but produced no usable output, so the doc-generation seam (and any agy delegation)
silently failed. Root cause (proven with `agy --log-file`): `agy` authenticates fine and the model **does**
generate a reply, **but on Windows agy's transcript writer builds a bogus POSIX path
(`/Users/<user>/.gemini/...`) and fails to persist the reply whenever the current working directory is on a
different DRIVE than HOME** — e.g. the project lives on `D:` / `I:` while HOME is on `C:`. Its stdout is
empty in headless mode too, so the answer was generated but lost. A secondary issue: the setup guide
**mis-advised** that an EOF on stdin "truncates the stream" — in reality a *clean EOF is required* for print
mode to complete, while an **open stdin hangs**. Together these made headless agy look broken.

**How it was solved.**
- **Added `scripts/agy_ask.ps1`** — a Windows-safe wrapper that (1) sets HOME, (2) forces the cwd onto the
  **same drive as HOME**, (3) gives stdin a **clean EOF** so print mode completes, (4) passes the prompt as a
  single argument, and (5) sets an explicit `--model`; it then reads the reply from the newest
  `transcript_full.jsonl`. `-AddDir <dir>` grants a directory outside the cwd for write tasks. On failure it
  prints `AGY_UNAVAILABLE: <reason>` so the caller can fall back.
- **Rewrote `docs/ai-workflow/antigravity_automation_setup_guide.md`** — documented the cross-drive root
  cause as the #1 failure (§3 gotcha), recommended the wrapper, **corrected the stdin advice** (clean EOF
  completes and does not truncate; an open stdin hangs), fixed the manual recipe and the pitfalls table.
- **`ANTIGRAVITY.md`** — the headless-invocation note now points at the wrapper and the drive caveat.
- _(POSIX — macOS / Linux — has no drive letters, so this fault does not occur there; the plain recipe works.)_

### Added — `/kit:recommend` is now tri-engine; new `/kit:checkpoint` (kit now ships all five `/kit:*`)

- **`/kit:recommend` → tri-engine.** Now Claude + Codex **+ Antigravity** (was Claude + Codex only). agy is
  dispatched via the wrapper as a **read-only scorer** (logic only, no pytest) — it is still **not** a code
  reviewer (the R0–R4 review loop stays Codex). Synthesis handles unanimous / majority / three-way split,
  with graceful per-engine fallback.
- **New `.claude/commands/kit/checkpoint.md`** — the write-side complement of `/kit:resume-break` (records a
  clean break point + a paste-able resume prompt after a fact-layer check). The kit now ships **all five**
  `/kit:*` commands: `auto-harness · harness-verify · recommend · resume-break · checkpoint`.
- Reconciled the agy role across `README.md`, `AGENTS.md` (§12.1 / §12.5), `.harness.toml`, `ANTIGRAVITY.md`,
  the setup guide, and `TEMPLATE_MANIFEST.md`: **agy = documentation writer + read-only `/kit:recommend`
  scorer** (the "not a code reviewer" rule is unchanged).
