"""run_codex_review_bridge.py - file-based bridge to an independent reviewer (e.g. Codex).

Provides write/run/archive/hygiene utilities for handing a diff/prompt to an
independent review agent through a bridge directory, then parsing its JSON
verdict. The actual reviewer call is fully injectable (the `codex_exec`
parameter), so tests can mock it without any real subprocess or network
activity.

WHERE THIS FITS (kit seams - reference, do not duplicate):
    * config (paths, thresholds, safety boundary) ... .harness.toml
    * 6-stage gate spec ............................. docs/_harness/quality-gates.md
    * task-id grammar / PROMPT-ID convention ........ docs/_harness/TASK_ID_GRAMMAR.md
    * independent-reviewer R0-R4 protocol ........... docs/ai-workflow/codex_claude_review_protocol.md
    * Claude subagents (RED/GREEN/FIX/AUDIT) ........ .claude/agents/{test-writer,impl-coder,refactor-fixer,score-auditor}.md

This module is the *transport + hygiene* layer only. It does NOT implement the
gate decision logic; it carries a request to the reviewer and returns the
reviewer's verdict dict (the policy - stability > security > maintainability >
visibility + no temporary fixes, the stop-trigger axes, the R0-R4 stage loop,
fact-layer local re-run vs logic-layer reviewer gating - lives in the protocol
doc above and in the reviewer agent itself).

The independent-reviewer overlay is OPTIONAL. Enable it per project via
`.harness.toml [review_overlay].enabled = true`. The session id and reviewer
binary invocation are project configuration, never hardcoded here.

Public API:
    write_request(prompt_id, content, bridge_dir) -> Path
    run_codex_review(request_path, session_id, *, codex_exec) -> dict
    archive_processed(prompt_id, bridge_dir) -> None
    assert_payload_clean(obj) -> None

Reviewer invocation note (project-configured, shown for orientation only):
    The headless reviewer is typically called with a read-only, repo-detached
    sandbox, resuming a known session, for example:

        codex exec --sandbox read-only --skip-git-repo-check \\
            -C <SCRATCH_DIR> -o <REPLY_PATH> resume <SESSION_ID> -

    The concrete `codex_exec` callable that runs this is injected by the caller;
    <SESSION_ID> and <SCRATCH_DIR> come from project config, not this module.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# prompt_id allowlist: alphanumerics, underscore, dot, hyphen only.
# First character must be alphanumeric to reject dot-only values like ".", "..".
# Matches the kit's PROMPT-ID format (e.g. <TASK_ID>_<STAGE>_<TYPE>_<YYYYMMDD>_<NN>,
# such as M3-RT-PERSIST-01_R2_GREEN_20260609_163). See docs/_harness/TASK_ID_GRAMMAR.md.
# ---------------------------------------------------------------------------

_SAFE_PROMPT_ID: re.Pattern[str] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")


def _validate_prompt_id(pid: str) -> None:
    """Raise ValueError if pid contains path-traversal characters or is dot-only.

    Only alphanumerics, underscore, dot, and hyphen are permitted.
    The first character must be alphanumeric (rejects ".", "..", "..." etc.).
    Empty or None values also raise.

    Args:
        pid: The prompt_id string to validate.

    Raises:
        ValueError: If pid is falsy, starts with a non-alnum char, or contains
                    unsafe characters.
    """
    if not pid or not _SAFE_PROMPT_ID.fullmatch(pid):
        raise ValueError(f"unsafe prompt_id: {pid!r}")


# ---------------------------------------------------------------------------
# Hygiene patterns - values that must never appear in a reviewer payload.
# These are GENERIC leak detectors and apply to any project unchanged:
#   absolute .db path, raw SQL, secret keyword, exception traceback.
# (For project-specific forbidden content, extend via .harness.toml.)
# ---------------------------------------------------------------------------

_ABSOLUTE_DB_PATTERN: re.Pattern[str] = re.compile(
    r"(?:/[^\s]+\.db|[A-Za-z]:\\.+?\.db)"
)
_RAW_SQL_PATTERN: re.Pattern[str] = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|JOIN)\b",
    re.IGNORECASE,
)
# Whole-word patterns applied to string leaf values only (not key names).
# Prevents false positives from key names like "nonsecret" or "secret_count".
_SECRET_PATTERN: re.Pattern[str] = re.compile(
    r"\b(api_secret_key|secret)\b",
    re.IGNORECASE,
)
_TRACEBACK_PATTERN: re.Pattern[str] = re.compile(r"Traceback \(most recent call last\)")


def write_request(
    prompt_id: str,
    content: str,
    bridge_dir: Path,
) -> Path:
    """Write a reviewer request to the bridge directory.

    Creates codex_request.md (returned path) and last_prompt.md,
    both containing the prompt_id and content.

    Args:
        prompt_id: Unique identifier for this review prompt. Must be non-empty.
        content: The review request content/diff text.
        bridge_dir: Directory where bridge files are written.

    Returns:
        Path to the created codex_request.md file.

    Raises:
        ValueError: If prompt_id is falsy (empty or None).
        AssertionError: If content leaks a secret / raw SQL / absolute .db path / traceback
            (enforced via assert_payload_clean — outbound hygiene).
    """
    _validate_prompt_id(prompt_id)  # raises ValueError on unsafe input

    # Outbound hygiene — enforced HERE, not left to the caller: refuse to write a request that would
    # leak secrets / raw SQL / absolute .db paths / tracebacks to the external reviewer. A forgotten
    # caller-side check can no longer bypass it (assert_payload_clean used to be a helper only).
    assert_payload_clean({"prompt_id": prompt_id, "content": content})

    bridge_dir.mkdir(parents=True, exist_ok=True)

    body = f"# Codex Review Request\n\nPrompt-ID: {prompt_id}\n\n{content}\n"

    request_path = bridge_dir / "codex_request.md"
    request_path.write_text(body, encoding="utf-8")

    last_prompt_path = bridge_dir / "last_prompt.md"
    last_prompt_path.write_text(body, encoding="utf-8")

    return request_path


def run_codex_review(
    request_path: Path,
    session_id: str,
    *,
    codex_exec: Callable[..., str],
) -> dict[str, Any]:
    """Execute an independent review using the provided codex_exec callable.

    Reads the request file, calls codex_exec with the content and session_id,
    then parses the returned JSON into a dict. Returns a stop sentinel dict
    on parse failure or if codex_exec raises.

    Args:
        request_path: Path to the codex_request.md file.
        session_id: Session identifier passed to codex_exec (project config;
                    e.g. <SESSION_ID> resumed by the headless reviewer).
        codex_exec: Injectable callable that accepts (content, session_id)
                    and returns a JSON string. Tests inject a MagicMock.

    Returns:
        Parsed review dict on success, or a stop-sentinel dict on failure.
    """
    try:
        content = request_path.read_text(encoding="utf-8")
        # Outbound hygiene guard: even if this request file was not produced by write_request,
        # never send a payload with secrets / SQL / db-paths / tracebacks to the reviewer.
        assert_payload_clean({"prompt_id": "outbound", "content": content})
        raw: str = codex_exec(content, session_id)
        parsed: dict[str, Any] = json.loads(raw)
        return parsed
    except AssertionError:
        _log.error("outbound payload hygiene violation in run_codex_review")
        return {
            "action": "stop",
            "error_type": "PayloadHygiene",
            "phase": "payload_hygiene",
            "error": "outbound payload is not clean",
        }
    except json.JSONDecodeError as exc:
        # Log full detail internally; never expose raw reply or exc text in payload.
        _log.exception("json_parse error in run_codex_review")
        return {
            "action": "stop",
            "error_type": type(exc).__name__,
            "phase": "json_parse",
            "error": "codex review failed",
        }
    except Exception as exc:
        # Log full detail internally; never expose exc message in payload.
        _log.exception("codex_exec error in run_codex_review")
        return {
            "action": "stop",
            "error_type": type(exc).__name__,
            "phase": "codex_exec",
            "error": "codex review failed",
        }


def archive_processed(prompt_id: str, bridge_dir: Path) -> None:
    """Move processed bridge files into processed/<prompt_id>/ subdirectory.

    Moves codex_request.md and last_prompt.md (if present) from bridge_dir
    into bridge_dir/processed/<prompt_id>/. Creates the destination directory
    as needed.

    Args:
        prompt_id: The prompt identifier used to name the archive subdirectory.
            Must pass _validate_prompt_id (alphanumerics, _, ., - only).
        bridge_dir: The bridge directory containing the files to archive.

    Raises:
        ValueError: If prompt_id contains unsafe path characters.
        ValueError: If resolved destination escapes bridge_dir (confinement guard).
        FileNotFoundError: If codex_request.md does not exist in bridge_dir.
    """
    _validate_prompt_id(prompt_id)  # reject path-traversal characters early

    dest_dir = bridge_dir / "processed" / prompt_id

    # Confinement guard: resolved path must stay inside bridge_dir.
    try:
        dest_dir.resolve().relative_to(bridge_dir.resolve())
    except ValueError:
        raise ValueError(
            f"archive destination escapes bridge_dir: {dest_dir!r}"
        ) from None

    dest_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("codex_request.md", "last_prompt.md"):
        src = bridge_dir / filename
        if src.exists():
            shutil.move(str(src), str(dest_dir / filename))


def _iter_string_leaves(obj: Any) -> list[str]:
    """Recursively collect all string leaf values from a nested dict/list structure.

    Only inspects dict values and list elements, not dict keys, to avoid
    false positives from benign key names like 'nonsecret' or 'secret_count'.

    Args:
        obj: Any object to recurse into.

    Returns:
        Flat list of all string leaf values found.
    """
    leaves: list[str] = []
    if isinstance(obj, str):
        leaves.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            leaves.extend(_iter_string_leaves(v))
    elif isinstance(obj, list | tuple):
        for item in obj:
            leaves.extend(_iter_string_leaves(item))
    return leaves


def assert_payload_clean(obj: Any) -> None:
    """Assert that a reviewer payload contains no sensitive or dangerous content.

    Checks all string leaf values (dict values only, not key names) for:
    - Absolute .db file paths (Unix or Windows)
    - Raw SQL statements (SELECT, INSERT, UPDATE, DELETE, JOIN)
    - Secret keywords (api_secret_key, secret) as whole words
    - Exception tracebacks

    Also requires that prompt_id is present in the payload dict.

    Args:
        obj: The payload object to inspect (expected to be a dict).

    Raises:
        AssertionError: If obj is None, missing prompt_id, or contains
                        forbidden content patterns.
        ValueError: Alternative to AssertionError for pattern violations.
    """
    if obj is None:
        raise AssertionError("payload must not be None")

    if not isinstance(obj, dict):
        raise AssertionError("payload must be a dict")

    if "prompt_id" not in obj:
        raise AssertionError("payload missing required field: 'prompt_id'")

    # Scan only string leaf values, not key names, to avoid false positives.
    for leaf in _iter_string_leaves(obj):
        if _ABSOLUTE_DB_PATTERN.search(leaf):
            raise AssertionError("payload contains absolute .db path")

        if _RAW_SQL_PATTERN.search(leaf):
            raise AssertionError("payload contains raw SQL statement")

        if _SECRET_PATTERN.search(leaf):
            raise AssertionError("payload contains secret keyword")

        if _TRACEBACK_PATTERN.search(leaf):
            raise AssertionError("payload contains exception traceback")
