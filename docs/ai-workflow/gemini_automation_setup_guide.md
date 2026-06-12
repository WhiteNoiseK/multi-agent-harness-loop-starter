# Gemini CLI Headless Setup Guide — Document / Wiki Generation

> Role: Gemini is NOT a code reviewer in this project.
> Gemini's role = headless document and LLM wiki generation tasks.
> Code review remains Claude (Writer) ↔ Codex (Reviewer).

---

## 0. What this builds

```
Claude identifies a doc/wiki generation task
  -> builds a generation prompt
  -> sends it headless to Gemini via `gemini -p`
  -> captures the output to a file
  -> Claude reads it and commits / integrates the result
Human copy-paste: 0 times.
```

Typical use cases:
- Foam knowledge-base entries (`docs/` wikis, MOC updates)
- `research.md` section drafts from raw notes
- Product/technical document generation from structured data
- Changelog or release-note drafts
- Any task where Gemini's large context window or writing style is preferred

---

## 1. Preflight

```powershell
gemini --version      # 0.46.0+
gemini auth status    # must show authenticated
```

---

## 2. Permission — add manually to `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(codex exec:*)",
      "Bash(gemini -p *:*)",
      "Bash(gemini --resume *:*)"
    ]
  }
}
```

Restart the Claude Code session after saving.

---

## 3. Core headless command

```powershell
# Write the generation prompt to a file
$prompt_file = Join-Path $env:TEMP "gemini_doc_prompt.txt"
$out_file    = Join-Path $env:TEMP "gemini_doc_out.txt"

# Write prompt content to file (avoids shell quoting issues with long text)
Set-Content -LiteralPath $prompt_file -Value $prompt_text -Encoding utf8

# Call Gemini headless
#   -p              non-interactive (headless) mode
#   --approval-mode plan   read-only — Gemini cannot modify project files
#   -m              model selection
$prompt = Get-Content -LiteralPath $prompt_file -Raw -Encoding utf8
gemini -p $prompt --approval-mode plan -m gemini-2.5-pro > $out_file

# Read result
Get-Content -LiteralPath $out_file -Raw -Encoding utf8
```

---

## 4. Session resume (for multi-turn doc generation)

```powershell
# List sessions
gemini --list-sessions

# Continue the most recent session
gemini --resume latest -p $prompt --approval-mode plan -m gemini-2.5-pro > $out_file
```

Use a **new session** when starting a new document topic.
Use **resume** when continuing / iterating on the same document.

---

## 5. Typical workflow (Claude orchestrates)

```
1. Claude reads the source material (notes, data, spec)
2. Claude builds a generation prompt (topic, structure, length, format)
3. Claude sends headless to Gemini → captures output file
4. Claude reviews the generated content for accuracy / consistency with project docs
5. Claude integrates the result into the target doc (editing / committing)
```

Claude is always the final integrator — Gemini output is treated as a **first draft**.
Claude must verify factual accuracy against single-authority specs before committing.

---

## 6. Pitfalls

| Problem | Fix |
|---|---|
| Interactive mode opens instead of headless | ensure `-p` flag is present |
| Non-ASCII (Korean) in prompt → garbled | write prompt to temp file with `Set-Content -Encoding utf8`; pass via `Get-Content -Raw` |
| ANSI color codes in output file | strip with `$text -replace '\x1b\[[0-9;]*m', ''` |
| Output is empty | check `gemini auth status`; add `-d` once for debug output |
| `--approval-mode plan` ignores tool calls | expected — plan mode is read-only; Gemini answers from its model only |

---

## 7. First validation

```powershell
gemini -p "Return the text: GEMINI_OK" --approval-mode plan -m gemini-2.5-pro
```

Expected: the text `GEMINI_OK`. If it returns text, the setup is complete.

---

## Related seams

- Code review loop (Codex, NOT Gemini): `docs/ai-workflow/codex_automation_setup_guide.md`
- Loop policy: `docs/ai-workflow/codex_loop_operating_policy.md`
- Config: `.harness.toml [review_overlay]` (Gemini not listed — intentional)
