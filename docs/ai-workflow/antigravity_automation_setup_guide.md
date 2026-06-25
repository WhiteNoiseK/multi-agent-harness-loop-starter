# Antigravity CLI (`agy`) Headless Setup Guide — Document / Wiki Generation

> Role: Antigravity is NOT a code reviewer in this project.
> Antigravity's role = headless document and LLM wiki generation tasks.
> Code review remains Claude (Writer) ↔ Codex (Reviewer).
>
> Antigravity (`agy`) is powered by Gemini models and replaces the former standalone Gemini CLI
> as this kit's headless doc engine. The role and constraints are unchanged (see `ANTIGRAVITY.md`);
> only the CLI and its invocation differ.

---

## 0. What this builds

```
Claude identifies a doc/wiki generation task
  -> builds a generation prompt
  -> sends it headless to Antigravity via `agy -p` (print / non-interactive mode)
  -> captures the response (stdout, or the conversation transcript — see §3.1)
  -> Claude reads it and commits / integrates the result
Human copy-paste: 0 times.
```

Typical use cases:
- Foam knowledge-base entries (`docs/` wikis, MOC updates)
- `research.md` section drafts from raw notes
- Product/technical document generation from structured data
- Changelog or release-note drafts
- Any task where a large context window or a different writing style is preferred

---

## 1. Preflight

```powershell
agy --help            # confirms `agy` is on PATH; -p / --print = headless single-prompt mode
agy models            # lists available model IDs (interactive; also confirms you are logged in)
```

- **Authentication**: Antigravity uses the same Google account as the Antigravity IDE. Complete the
  browser OAuth flow **once** by running `agy` interactively (press Enter to open the browser, paste
  the code back). Headless runs reuse the cached keyring token — they **cannot** perform a first-time
  login, so do the interactive login before automating.

---

## 2. Permission — add manually to `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(codex exec:*)",
      "Bash(agy -p *:*)",
      "Bash(agy -c *:*)",
      "Bash(agy --conversation *:*)"
    ]
  }
}
```

Restart the Claude Code session after saving.

---

## 3. Core headless command

`agy -p` runs a single prompt non-interactively and prints the response (`--print` and `--prompt` are equivalent aliases of `-p`). The `.claude/settings.json` allowlist in §2 covers `agy -p` plus the resume forms `agy -c` / `agy --conversation`.

```powershell
# Write the generation prompt to a file (avoids shell-quoting issues with long / non-ASCII text)
$prompt_file = Join-Path $env:TEMP "agy_doc_prompt.txt"
$out_file    = Join-Path $env:TEMP "agy_doc_out.txt"
Set-Content -LiteralPath $prompt_file -Value $prompt_text -Encoding utf8
$prompt = Get-Content -LiteralPath $prompt_file -Raw -Encoding utf8

# Call Antigravity headless
#   -p / --print                     non-interactive (headless) mode; prints the response
#   --dangerously-skip-permissions   auto-approve tool-permission prompts (a GUI/TUI popup
#                                     cannot be answered from a background/headless caller)
#   --model <id>                     optional model override (see `agy models`)
#   --print-timeout 120s             max wait for the response (default 5m)
agy -p $prompt --dangerously-skip-permissions --print-timeout 120s > $out_file 2>&1

Get-Content -LiteralPath $out_file -Raw -Encoding utf8
```

> **Why `--dangerously-skip-permissions` is required headlessly.** Without it, `agy` raises an
> interactive tool-permission prompt that a background/headless caller cannot answer, so the command
> **hangs indefinitely**. The flag auto-approves those prompts. (Alternative: set
> `toolPermission = "always-proceed"` in `~/.gemini/antigravity-cli/settings.json` — see §6.)

### 3.1 Robust capture — read the conversation transcript

In some non-interactive / sandboxed contexts `agy --print` exits as soon as the model stream
starts, **before flushing the answer to stdout** — `$out_file` is empty even though the model
answered. The answer is **always** persisted to the conversation transcript, so capture it there:

```powershell
# After the agy call above: read the newest conversation transcript and extract the model reply
$brain = Join-Path $env:USERPROFILE ".gemini\antigravity-cli\brain"
$tr = Get-ChildItem "$brain\*\.system_generated\logs\transcript_full.jsonl" |
      Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content -LiteralPath $tr.FullName -Encoding utf8 |
  ForEach-Object { $_ | ConvertFrom-Json } |
  Where-Object { $_.type -eq 'PLANNER_RESPONSE' -and $_.source -eq 'MODEL' } |
  Select-Object -Last 1 -ExpandProperty content
```

- Transcript path: `~/.gemini/antigravity-cli/brain/<conversationId>/.system_generated/logs/transcript_full.jsonl`
- Each line is one JSON step; the model reply is the step with `type = "PLANNER_RESPONSE"` and
  `source = "MODEL"` — its `content` field is the answer (its `thinking` field is the reasoning trace).
- This transcript path is the reliable capture method in fully headless contexts — **prefer it over
  parsing stdout** when automating. Do not rely on a stdin trick (`< /dev/null` gives an immediate
  EOF that can truncate the stream; an open stdin can hang). The transcript is the source of truth.

---

## 4. Session resume (for multi-turn doc generation)

```powershell
agy -c -p $prompt --dangerously-skip-permissions                    # -c / --continue : continue the most recent conversation
agy --conversation <ID> -p $prompt --dangerously-skip-permissions   # resume a specific conversation by ID
```

Conversation IDs are the folder names under `~/.gemini/antigravity-cli/brain/` (and `.../conversations/`).
Use a **new** call (no `-c`) for a new document topic; **continue / resume** when iterating on the same one.

---

## 5. Typical workflow (Claude orchestrates)

```
1. Claude reads the source material (notes, data, spec)
2. Claude builds a generation prompt (topic, structure, length, format)
3. Claude sends headless to Antigravity → captures the reply (stdout or transcript §3.1)
4. Claude reviews the generated content for accuracy / consistency with project docs
5. Claude integrates the result into the target doc (editing / committing)
```

Claude is always the final integrator — Antigravity output is treated as a **first draft**.
Claude must verify factual accuracy against single-authority specs before committing.

---

## 6. Pitfalls

| Problem | Fix |
|---|---|
| Command hangs, no output | add `--dangerously-skip-permissions` (a permission popup is blocking); make sure you are not waiting on an open stdin |
| `$out_file` is empty though the model answered | print mode exited before flushing stdout — read the transcript (§3.1); this is the reliable path when headless |
| Non-ASCII (Korean) in prompt → garbled | write the prompt to a temp file with `Set-Content -Encoding utf8`, pass via `Get-Content -Raw` |
| Logs show `not logged into Antigravity` | complete the browser OAuth once by running `agy` interactively (logs: `~/.gemini/antigravity-cli/log/*.log`) |
| Want zero popups permanently | set `toolPermission = "always-proceed"` in `~/.gemini/antigravity-cli/settings.json` (`trustedWorkspaces` may also list the project path) |
| A stale `agy` process holds a lock and later calls hang | kill leftover `agy` processes (`Get-Process agy | Stop-Process -Force`) and retry |

---

## 7. First validation

```powershell
agy -p "Return the text: AGY_OK" --dangerously-skip-permissions --print-timeout 60s
```

Expected: the text `AGY_OK`. If stdout is empty, read the newest transcript (§3.1) — the reply
should contain `AGY_OK`. Either way, if the text comes back, the setup is complete.

---

## Related seams

- Code review loop (Codex, NOT Antigravity): `docs/ai-workflow/codex_automation_setup_guide.md`
- Loop policy: `docs/ai-workflow/codex_loop_operating_policy.md`
- Constraints: `ANTIGRAVITY.md`
- Config: `.harness.toml [review_overlay]` (Antigravity not listed as a reviewer — intentional)
