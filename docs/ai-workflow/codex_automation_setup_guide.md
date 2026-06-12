# Claude <-> Codex Automated Review Setup Guide (codex CLI headless)

> Purpose: paste/reference this whole file into another project's Claude so it can pull Codex independent reviews without any human copy-paste.
> Verified end-to-end (install / auth / session resume / verdict capture).
> Project-agnostic: replace the `<...>` placeholders and it works anywhere.
> Language note: kept ASCII English on purpose (cp949/Windows viewers render Korean .md as mojibake; Codex is ASCII-oriented).

---

## 0. What this builds

```
Claude writes a review prompt
  -> sends it headless to Codex via `codex exec`
  -> captures the verdict to a file (reply.txt)
  -> Claude reads it and decides the next step
Human copy-paste: 0 times.
```

### Two limits you MUST internalize first (the core of the design)

1. **The VS Code Codex extension chat window != the CLI session.**
   A message sent via the CLI does NOT appear in the extension chat window (separate live state). So this is a headless loop; visibility comes only from the file (`reply.txt`). Give up on real-time extension-window sync.

2. **A read-only Codex cannot re-run pytest etc.**
   Codex honestly answers `"logical review only, no rerun claim"`. So a Codex PASS is a "logic review", NOT fact verification.
   => NEVER proceed on a Codex PASS alone. Always re-run `pytest/mypy/ruff` locally and confirm `claimed == actual`.
   => Codex = independent logic layer / local re-run = fact layer. Both must be AND-ed to pass.

---

## 1. Preflight (run first)

```powershell
codex --version            # install check
codex login status         # must show "Logged in using ChatGPT"
codex exec --help          # exec options (--sandbox, -C, -o, --output-schema, --skip-git-repo-check)
```

- Not installed: `npm i -g @openai/codex`
- Not authed: `codex login` (browser once) or `printenv OPENAI_API_KEY | codex login --with-api-key`

---

## 2. Permission - the user must add it (the agent cannot)

`codex exec` is an external (OpenAI) send, so the Claude Code guardrails block it.
The agent editing its own `.claude/settings.json` to widen permissions is ALSO blocked.

So ask the user directly:

> "Add the single line `"Bash(codex exec:*)"` to the `permissions.allow` array in `.claude/settings.json` (restart the session if needed)."

This is required to pass the auto-mode data-exfiltration classifier. (Either global `~/.claude/settings.json` or project `.claude/settings.json`; project-scoped is least-privilege and recommended.)

---

## 3. Find the session (to continue an existing Codex thread)

```powershell
# search by session title
Get-Content "$env:USERPROFILE\.codex\session_index.jsonl" -Encoding utf8 | Select-String "<project_keyword>"

# or search session files by a task marker (the UUID is in the filename)
Get-ChildItem "$env:USERPROFILE\.codex\sessions" -Recurse -Filter "rollout-*.jsonl" |
  ForEach-Object { if (Select-String -LiteralPath $_.FullName -Pattern "<TASK_ID>" -SimpleMatch -Quiet) { $_.Name } }
```

- Session ID = UUID (e.g. `<SESSION_ID>`).
- To start fresh, just `codex exec` without resume.

---

## 4. The core command (exact syntax - options go BEFORE resume)

```powershell
$h = "<path to the review prompt file (.md)>"
$tmp = Join-Path $env:TEMP "codex_scratch"; New-Item -ItemType Directory -Force $tmp | Out-Null
$reply = Join-Path $tmp "reply.txt"

Get-Content -LiteralPath $h -Raw -Encoding utf8 |
  codex exec --sandbox read-only --skip-git-repo-check -C $tmp -o $reply resume <SESSION_ID> -

Get-Content -LiteralPath $reply -Raw -Encoding utf8     # <- read the Codex verdict
```

| Option | Meaning |
|---|---|
| `--sandbox read-only` | Codex cannot modify files (safe) |
| `--skip-git-repo-check -C $tmp` (empty dir) | sends ONLY the handoff text, no repo files leave (handoff-only) |
| `-C <repo path>` (alternative) | Codex reads/verifies the real code (repo files are sent) |
| `-o $reply` | capture Codex's final answer to a file -> read+parse it |
| stdin `-` | prompt from stdin; pipe long text instead of an arg |
| `--output-schema <schema.json>` | (optional) Codex must reply with that JSON schema -> stable parsing |

**Notes:**
- Options MUST come before `resume` (exec level). Placing them after `resume` throws a `Usage:` error.
- New session: drop the `resume <SESSION_ID> -` part and put `"prompt"` directly at the end.

---

## 5. Pitfalls (all hit for real - check here when stuck)

- **PowerShell ExecutionPolicy**: running `codex` (=`codex.ps1`) interactively may error "cannot run scripts". Claude's tool env is usually fine; if blocked, call `codex.cmd` directly or `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **Non-ASCII (e.g. Korean) username path**: bash `$HOME` / `~` corrupts a non-ASCII path (mojibake). => use PowerShell + `$env:USERPROFILE` + `-LiteralPath`.
- **stderr noise**: `codex login status` etc. may print red NativeCommandError; if the content is correct it succeeded (just node stderr).
- **resume = append to the same file** (not a fork), keeps the canonical rollout format -> the session does not break (JSONL integrity confirmed).
- **"Not inside a trusted directory"**: appears when `-C` is a non-git folder -> add `--skip-git-repo-check`.

---

## 6. Safety gate (mandatory - the essence of the automation)

After receiving a verdict:

1. **Re-run locally**: `pytest / ruff / black / mypy` -> confirm `+-0` match against Codex claimed numbers (blocks forged PASS).
2. **Severity decision**:
   - LOW / NIT / PASS + local-verify OK + no safety-boundary touch -> auto next step.
   - MEDIUM+ / local mismatch / verdict BLOCKED/ADJUST / safety boundary (any path under `[safety_boundary]` in `.harness.toml` / destructive cmd / production deploy / out-of-scope dirty / single-authority spec / [HARNESS] commit) -> STOP and report to the user.
3. Start with **dry-run** (no auto-commit, just report "this is what I would do") for a few cycles to build trust, then switch to auto.

> Safety-boundary paths are project-specific: configure them per project in `.harness.toml [safety_boundary]`. The examples in that file are generic illustrations only.

---

## 7. Data caution

`codex exec` sends the prompt (+ the files Codex reads if `-C <repo>`) to OpenAI = the SAME path the user already uses with the Codex extension. But:
- Automate only AFTER the section-2 permission (explicit user approval).
- NEVER send/commit `secret` / `.env` / `credential` / tokens.

---

## 8. First validation order (test exactly like this)

1. Run section 1 (preflight) -> confirm `codex exec` works.
2. Ask the user for the section-2 permission.
3. Test the section-4 command with a short probe: send `"Return only OK"` as a NEW session and check `reply.txt` says "OK".
4. If it works, do one real review-prompt round-trip + one cycle of the section-6 gate (local re-run cross-check).
5. Report the result to the user and agree on the auto scope (dry-run -> live).

---

## Appendix - one-line summary

> A Codex PASS is only a "logic review" -> ALWAYS cross-check with a local re-run + external send/permission needs user approval + the window does not sync so read from a file. Honor these three and the automation is safe.

---

## Related seams (kit references, not duplicated here)

- Config (safety boundaries, gate thresholds): `.harness.toml`
- 6-stage quality-gate spec: `docs/_harness/quality-gates.md`
- Independent-reviewer protocol (R0-R4, 5-priority policy, stop triggers, PROMPT-ID convention): `docs/ai-workflow/codex_claude_review_protocol.md`
- Loop operating policy: `docs/ai-workflow/codex_loop_operating_policy.md`
- Stage subagents (already present): `.claude/agents/{test-writer,impl-coder,refactor-fixer,score-auditor}.md`
- Task id grammar: `docs/_harness/TASK_ID_GRAMMAR.md`
- Gemini doc/wiki generation (NOT code review): `docs/ai-workflow/gemini_automation_setup_guide.md`
