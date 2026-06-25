# CODEX.md — Raw Codex Execution Constraints

> **Universal harness rules (role table, stage assignment, "WRITE SCOPE IS CLOSED" template)**
> are defined in `AGENTS.md §12`. Read that section first — this file only covers
> raw `codex exec` specifics on top of the universal rules.

Raw `codex exec` runs are **closed-scope by default**.

> This file applies when Codex is invoked via raw `codex exec "..."` rather than a named agent
> in `.codex/agents/`. Named agents define their own constraints in their TOML files.
> This file is the fallback guard for all unagented calls.

---

## Write Scope

Only files **explicitly listed** in the user prompt may be created, modified, deleted,
formatted, or normalized.

If a task requires touching any unlisted file, **stop and report the required path** instead
of editing it.

---

## Always Forbidden (unless the prompt has an explicit ALLOW for that exact path)

```
docs/**
.claude/**
.codex/**
.harness.toml
AGENTS.md
CODEX.md
ANTIGRAVITY.md
CLAUDE.md
.clauderules
build / CI configuration files   (setup.py, pyproject.toml, .github/**, etc.)
project settings                  (*.cfg, *.ini at root)
safety-boundary paths             (see .harness.toml [safety_boundary].paths)
coding convention documents
```

---

## Deletes

**Never delete a file** unless the prompt has a dedicated `DELETE LIST:` section naming that
exact path.

---

## Git Hygiene

Before editing:
1. Run `git status --short` — do not touch pre-existing dirty files.

After editing:
1. Run `git diff --name-status`.
2. Final response **must list every changed path**.
3. If any changed path is outside the prompt's allowlist, **revert only that out-of-scope change**
   and report the incident — do not commit.

---

## Documentation and Progress Files

Do **not** update progress docs, lifecycle docs, planning docs, harness docs, or conventions
unless the user prompt explicitly lists those exact files.

---

## Commits

**Do not commit** unless the prompt explicitly says "commit" or "git commit".

---

## Prompt Template for Claude → Codex Handoff

When Claude calls `codex exec` for implementation tasks, the prompt must begin with:

```
WRITE SCOPE IS CLOSED.
Read AGENTS.md §12 and CODEX.md before starting.

You may create or modify ONLY these paths:
- <path 1>
- <path 2>

You must not create, modify, delete, format, or normalize any other file.
After finishing, run: git diff --name-status
Report every changed path. Revert any out-of-scope change before reporting.
Do not commit.
```
