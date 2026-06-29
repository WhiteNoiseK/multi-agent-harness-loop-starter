# /kit:checkpoint — record a clean break point + emit a resume prompt

The **write-side complement** of `/kit:resume-break`. When you need to stop mid-work (context getting long,
end of a logical phase, switching tasks), this captures the current coordinate into the durable fact layer so a
**fresh session resumes with zero loss and zero duplicate work** — and produces a paste-able resume prompt.
General-purpose: independent of task type. If `$ARGUMENTS` carries a hint (a note, the next stage), fold it in.

> `/kit:resume-break` READS the fact layer to restore. `/kit:checkpoint` WRITES the fact layer so that restore
> is clean. The two share the same entry points (progress.md break block · scores · git · handoffs) — keep them
> in lockstep: whatever resume-break reads first, checkpoint must write last.

## 1. Establish the coordinate (read-only first)

1. Current active task + the **pending stage/verdict** (what is done vs. what is next).
2. `docs/ai-workflow/scores/<task_id>.json` → the last recorded stage.
3. `git log --oneline --grep=HARNESS -5` → the last checkpoint SHA.
4. `git status --short` + `git diff --name-only` → your in-scope files vs. other-session dirty/untracked.

## 2. Verify the break is clean (fact layer — do NOT checkpoint over a mess)

- **claimed == actual** for the last *completed* stage: re-run its scope directly (`pytest <scope>` ·
  `mypy <src>` · `ruff`/`black`) and confirm the numbers you are about to record are real. Never write a
  claimed number you did not just observe.
- **No half-applied edits**: scan for partial files / duplicated blocks / orphan imports / broken syntax left
  by the stop. If found, **finish or revert that fragment before checkpointing** (a checkpoint must restore to
  a coherent state).
- **Committed-clean vs. uncommitted**: if your in-scope work is committed, record the SHA. If it is
  intentionally uncommitted (mid-stage), say so explicitly and list exactly which files — so resume-break does
  not mistake them for stragglers. Stage/commit **only your own files** (`git add <path>`; never `git add .` /
  `-A`); preserve other-session dirty files.

## 3. Write the break point (the three durable surfaces + memory)

1. **progress.md** — refresh the `🔴 현재 중단점 (BREAK POINT)` block, kept **at the very end of the file**
   (resume-break reads the end first). It must contain: active task · pending stage (what is next) · last
   commit SHA · the fact layer (claimed==actual numbers) · links to the locked design (scores + handoff) · the
   next PROMPT-ID + reviewer session id · a one-line scope summary · any **safety-boundary** caveat · the
   shared-tree staging rule · a link to the resume-prompt file.
2. **scores/<task_id>.json** — ensure the last stage entry exists; if stopping mid-stage, add a
   `checkpoint_note` (why stopping, what is locked, the next PROMPT-ID). Keep the JSON well-formed.
3. **Resume-prompt file** — write `docs/ai-workflow/RESUME_<task_id>_<YYYYMMDD>.md` containing a single
   fenced, paste-able prompt **in the user's language**. (Per the handoff-language split, user-paste prompts
   are the user's language; only `docs/ai-workflow/handoffs/*.md` reviewer handoffs are ASCII English — so the
   resume prompt lives **outside** `handoffs/`.) The prompt must be self-contained: current coordinate, locked
   scope, the execution style to preserve, the safety boundary, and the explicit next action (which stage to
   resume from — never re-run an already-CLOSED stage).
4. **Memory** — update the project's resume-prompt memory (e.g. `reference_resume_prompt_*`) + its `MEMORY.md`
   pointer so the coordinate survives even without the files in context.

## 4. Stop / confirm (do not checkpoint silently over these)

If any of the §2 checks fail, surface it instead of writing a misleading "clean" checkpoint:
- **Trust collapse** — claimed != actual / no fact layer to verify against.
- **Half-done fragment** — an incomplete edit that would not restore coherently.
- **Safety boundary** — an uncommitted change inside a `.harness.toml [safety_boundary]` path, or a pending
  real-HW/production action. Record it as a blocker in the break block; do not imply it is safe to resume.
- **Unapproved judgmental decision** — a frozen-test edit / scope expansion / contract reversal left pending.

## 5. Report (once)

Emit, in the session chat: `[checkpointed coordinate (task/stage)] · [committed SHA or "uncommitted: <files>"]
· [fact layer OK / N issues] · [resume entry: /kit:resume-break or the RESUME_*.md path] · [next action]`,
then print the paste-able resume prompt. End the loop here — do not start the next stage.

> Cross-refs: `/kit:resume-break` (the read-side) · `docs/ai-workflow/codex_loop_operating_policy.md` §3
> (the 5 stop axes) · the handoff-language split (user-paste = user's language, reviewer handoffs = ASCII English).
