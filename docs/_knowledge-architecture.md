# Knowledge Architecture Conventions (format SSOT)

> This document owns only the **format conventions** of `docs/` (file names, metadata, links, navigation structure).
> The **content authority** (which specification is the truth) is solely owned by [.claude/CLAUDE.md](../.claude/CLAUDE.md) **§8 Single-Authority Specifications** as the only SSOT;
> this document does not re-list that list (re-stating it would create divergence from §8).

| Item | Value |
|:---|:---|
| Current version | v0.1 |
| Created | {{TEMPLATE_BASELINE_DATE}} |
| Last updated | {{TEMPLATE_BASELINE_DATE}} |
| Status | authoritative |

---

## 1. Trust Model — Resolve Conflicts by a "Read-Time" Rule

As documents accumulate, conflicts arise on the same topic. Instead of synchronizing every file every time, decide which to trust **by the following rules at read time**.

1. If one side is **authority-registered** (`status: authoritative` or declared a "single-authority specification") → **the authoritative document wins.**
2. If neither is authoritative → **the more recent document (later last-updated date) wins.**
3. If high-risk items (spec values, constants, formulas, **operational/safety procedures** [paths registered in `.harness.toml` `[safety_boundary]` — e.g. shutdown, hardware adapters, wiring, etc.]) conflict, or **the judgment is doubtful** → **flag it to a human** (fail-safe — no automatic judgment). Aligned with the stability-first principle (absolutely no errors).

> In other words, trust = **authority registration** or **recency**. If it is old and not authoritative, trust is low (a candidate for deprecation).
> The danger is not "duplication" itself but **a copy diverging from the original (drift)**.

## 2. Two Document Conventions — Record Recency by Lifecycle

| Type | Convention | Reason |
|:---|:---|:---|
| **Snapshot** (handoff, audit, one-off report) | filename `name_YYYYMMDD.md` | created once, never edited → creation date = last date |
| **Living/authoritative** (spec, design, guide) | top metadata block (below) + a changelog line on each change | continuously updated → a filename date is unsuitable, track by last-updated date |

Top metadata block for a living document (required):

```
| Item | Value |
|:---|:---|
| Current version | vX.Y |          (required)
| Created | YYYY-MM-DD |              (optional — creation date)
| Last updated | YYYY-MM-DD |         (required — primary source for recency tracking)
| Status | [Authority Level] |        (required)
#authority/[type]/[level]             (required tag for Obsidian Graph View)
```

**Authority Taxonomy (Tags and Status):**

**1. Project Knowledge (Domain Authority)** — Actual content, specs, decisions.
- `#authority/domain/supreme` (Supreme Authority): The highest level project charter/goals (e.g., ProductProposal).
- `#authority/domain/single` (Single Authority / SSOT): The single source of truth for a specific domain (e.g., Data Spec, Legal Opinion).
- `#authority/domain/derived` (Derived / Non-authoritative): Working docs, snapshots, or research derived from authoritative sources.
- `#authority/domain/deprecated` (Deprecated): Abandoned ideas or old specs.

**2. System/Format Rules (System Authority)** — Rules on how to write docs and system conventions.
- `#authority/system/absolute` (Absolute Authority Rule): Inviolable core architecture rules (e.g., _knowledge-architecture.md).
- `#authority/system/active` (Active Rule): Currently active operational rules and templates.
- `#authority/system/inactive` (Inactive Rule): Rules that are currently not in use but kept for reference.
- `#authority/system/deprecated` (Deprecated Rule): Abandoned conventions. (Note: There is no "non-authoritative rule", as a rule without authority is not a rule.)

**Single-authority is a FILE-only label — distinguish it from "priority authority" (content):**
- `domain/single` is assigned ONLY when the WHOLE file is a frozen definition of one domain (the file wins on conflict — "if code differs, the code is wrong"). A working doc that mixes process/log/analysis with a few defined values is NOT single → `domain/derived`.
- Litmus (one question): "Does this **file** own a definition and **win** on conflict?" → single. "Is it **derived** and **yields** on conflict?" → derived. Decide by the file's ROLE, not by how important its content is.
- **Priority authority** = binding quantitative (performance/function) items INSIDE a derived working doc. They MUST be complied with, but the host file stays non-authoritative — do NOT give them an `#authority` tag (kept separate from the file-level system); mark them in-text as "priority authority".
- Lifecycle: priority-authority items accumulate inside derived docs → frozen at Gate P (or a domain freeze) → only THEN is a single-authority FILE (e.g. `docs/engineering/<spec>.md`) born. Hence early in a project the knowledge domain has few/no single-authority files.
- Process/working docs (plan, progress, research, logs, glossary, test plan, decisions, per-task docs) and **draft design specs** are ALWAYS `domain/derived`; reword any internal "single-authority" self-marking to "priority authority".

On change, add a line to the change-history table at the bottom of the document: `| Version | Date | Change | Decided by |`

> **This metadata block is a load-bearing (functionally depended-upon) convention.** `scripts/foam_catalog.py` parses the `Last updated` field
> as the primary recency signal to auto-generate `_recent.md` / `_authority.md`. Without the metadata block, that document falls back to
> filename/git/mtime, which lowers the reliability of the recency decision.

**Cohesion unit**: each document holds only **one cohesive topic/decision** (when the topic changes or the authority scope splits, start a new file). Apply the coding-style principle (many small files · 200-400 lines · organized by domain) to docs. — A clear cohesion unit also improves the quality of the §4 embedding (`Show Similar Notes`) recommendations.

## 3. File Naming Conventions

- **snake_case** (the common docs convention). e.g. `{{EXAMPLE_SPEC_STEM}}_data_spec.md`
- Wikilinks **exactly match the filename stem**: `[[{{EXAMPLE_SPEC_STEM}}_data_spec]]`
- If the display text differs, use the alias syntax: `[[file_stem|display text]]`

## 4. Link Conventions — Not "No Copy-Paste" but "Prevent Drift"

- When citing a high-risk fact (spec value, constant) in another document, attach an **inline copy + source tag** `[SSOT: path §x]` (traceable copy-paste). Pure link-only is not enforced.
- Narrative content (analysis, research, retrospective, summary) may be **freely duplicated** — self-containment (understanding from that document alone) improves readability.
- **A "## Related Documents" section is not mandatory in every document.** Manually link only the key relationships between authoritative documents, and delegate loose associations to Foam embedding (`Show Similar Notes`) suggestions.
- Link not to the content but to the **subsection heading**: `[[file_stem#section heading]]` (jumps exactly to that section).
- **Embedding (`Show Similar Notes`) results are only suggestions; do not auto-insert them into the body or links without human confirmation (R6).** What is auto-generated is limited to the most-recent catalog in §6.

## 5. Section Header Conventions — Protect Anchors

- H2 uses the `## N. Title` (number + title) format.
- **Do not renumber.** Add new sections by **appending at the end** or only as H3/H4 (to prevent existing `[[file#N. Title]]` links from breaking).
- However, **"Related Documents" and "Change History"** are treated as exceptions: unnumbered conventional sections.

## 6. Navigation Structure — A 2-Tier MOC (Map of Content — document index hub)

**[NOW · apply immediately]**
- **Domain = folder** (`ai-workflow/`, `engineering/`, `pm-guide/` …). The folder is itself the classification axis, so tags are unnecessary.

**[LATER · after tool adoption]**
- The root `docs/index.md` = a domain router (do not list individual files).
- A per-domain `_moc.md` = the index for that folder.
- The **most-recent catalog** = auto-generated by the generator in `scripts/` (not manually registered). Recency priority: ① `Last updated` → ② `Created`/`creation date` → ③ filename `_YYYYMMDD` (snapshot creation date) → ④ git commit date → ⑤ file mtime. (An explicit last-updated date is the most reliable recency signal.)

## 7. Authority Registry

**[LATER · after tool adoption]**
- `docs/_authority.md` gathers the authoritative documents (§8 + "single-authority specification" declarations + `status: authoritative`).
- However, **the content is owned by §8**, while `_authority.md`/`_knowledge-architecture.md` handle only **references and format** (orthogonal separation).
- `_authority.md` **does not list spec names/paths directly**; it links to §8 or parses §8 to **generate (generated, not hand-listed)** — applying the §4 `[SSOT]` principle to the registry itself to fundamentally prevent drift from §8.

## 8. The spec-header convention for field cascade (load-bearing)

`scripts/field_cascade.py` **automatically extracts** column names from the single-authority data spec to build `_field_cascade.md`
(field → the documents that use that field). For this, the data spec **must** include a §3.1 header block of the following form
(if this format breaks, the cascade stays empty):

````
### 3.1 Header definition (fixed order)

```text
Field1, Field2, Field3,
Field4, Field5(unit),
... (list the CSV header in fixed order)
```
````

- The code-block fence starts with ` ```text ` (matched by the regex `###\s*3\.1.*?```text`).
- If one column has two notations (CSV PascalCase + DB snake_case), the generator searches via an alias union, so
  also place the snake_case notation in the spec's DB mapping section (prevents 30-50% omission).
- For the canonical skeleton of a data spec, see [`engineering/_TEMPLATE_data_spec.md`](engineering/_TEMPLATE_data_spec.md).

---

## Change History

| Version | Date | Change | Decided by |
|:---|:---|:---|:---|
| v0.1 | {{TEMPLATE_BASELINE_DATE}} | template baseline — the canonical format conventions at the time of starter-kit extraction (trust model, two conventions, file naming, links, headers, MOC, authority registry, field-cascade spec-header convention). Project content is owned by §8 (orthogonal separation). | {{ARCHITECT}} |
