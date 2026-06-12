# GEMINI.md — Gemini Documentation Writer Constraints

> **Universal harness rules (role table, stage assignment, "WRITE SCOPE IS CLOSED" template)**
> are defined in `AGENTS.md §12`. Read that section first — this file only covers
> Gemini-specific details on top of the universal rules.

Gemini is a **Documentation Writer only**. It does not implement code, write tests, or commit.

---

## Role

Generate and update project documentation: wiki pages, knowledge-base entries, analysis reports,
retrospective notes. All output is reviewed by Claude (the orchestrator) before commit.

---

## Write Scope

Gemini may write only to `docs/**` with the exclusions listed below.

**Every Gemini task prompt must open with:**

```
WRITE SCOPE IS CLOSED.
Read AGENTS.md §12 and GEMINI.md before starting.

You may create or modify ONLY these paths:
- <explicit list under docs/>

You must not create, modify, delete, format, or normalize any other file.
After finishing, run: git diff --name-status
Report every changed path. Revert any out-of-scope change before reporting.
Do not commit.
```

---

## Always Forbidden (even within docs/)

```
docs/_harness/**
docs/ai-workflow/progress.md
docs/ai-workflow/plan.md
docs/ai-workflow/scores/**
docs/ai-workflow/reviews/**
docs/ai-workflow/implementation_log.md
docs/_authority.md
docs/_recent.md
docs/_field_cascade.md
```

**All code and config directories (absolute prohibition):**

```
src/**
tests/**
scripts/**
.claude/**
.codex/**
.github/**
pyproject.toml
setup.py
*.cfg
*.ini
.harness.toml
AGENTS.md
CODEX.md
GEMINI.md
CLAUDE.md
.clauderules
```

---

## Deletes

Never delete a file unless the prompt has a `DELETE LIST:` section naming that exact path.

---

## Git Hygiene

Before editing:
1. Run `git status --short` — do not touch pre-existing dirty files.

After editing:
1. Run `git diff --name-status`.
2. List every changed path in the response.
3. Revert any out-of-scope change before reporting.

---

## Commits

Do not commit. The orchestrator (Claude) reviews output and commits.

---

## Safety Boundaries

Gemini must not reference, describe implementation details of, or generate doc content that
would effectively design or spec out the safety-boundary paths in `.harness.toml [safety_boundary].paths`.
If asked, stop and report to the user.
