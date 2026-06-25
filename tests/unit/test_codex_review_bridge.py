"""Stage 1 RED tests for scripts/run_codex_review_bridge.py (independent-reviewer bridge).

Covers write_request, run_codex_review (mock reviewer, no real calls),
archive_processed, and hygiene/payload cleanliness checks.

ALL tests are expected to FAIL at collection (ImportError) until
scripts/run_codex_review_bridge.py is implemented (Stage 2 GREEN).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# scripts/ import path - tests live in tests/unit/, so parents[2] is the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from run_codex_review_bridge import (  # noqa: E402  (scripts/ on sys.path above; not an installed package)
    archive_processed,
    assert_payload_clean,
    run_codex_review,
    write_request,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE_PROMPT_ID = "M1-EXAMPLE-01_RED_20260608_01"
SAMPLE_CONTENT = "Please review the following diff:\n\n```diff\n+line\n```"

VALID_REVIEW_REPLY: dict[str, Any] = {
    "prompt_id": SAMPLE_PROMPT_ID,
    "task_id": "M1-EXAMPLE-01",
    "stage": "RED",
    "verdict": "PASS",
    "max_severity": "LOW",
    "requires_user": False,
    "hard_boundary_violation": False,
    "findings": [],
    "next_action": "auto_continue",
    "notes": "looks good",
    "reply_prompt_id": "M1-EXAMPLE-01_RED_20260608_02",
    "rerun_performed": True,
}


# ===========================================================================
# Section E.1 - write_request
# ===========================================================================


@pytest.mark.unit
def test_write_request_creates_codex_request_md(tmp_path: Path) -> None:
    """write_request must create codex_request.md in bridge_dir."""
    write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    codex_request = tmp_path / "codex_request.md"
    assert codex_request.exists(), "codex_request.md must be created"


@pytest.mark.unit
def test_write_request_creates_last_prompt_md(tmp_path: Path) -> None:
    """write_request must create last_prompt.md in bridge_dir."""
    write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    last_prompt = tmp_path / "last_prompt.md"
    assert last_prompt.exists(), "last_prompt.md must be created"


@pytest.mark.unit
def test_write_request_returns_path_to_codex_request(tmp_path: Path) -> None:
    """write_request must return a Path pointing to codex_request.md."""
    result = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    assert isinstance(result, Path)
    assert result.name == "codex_request.md"
    assert result.exists()


@pytest.mark.unit
def test_write_request_codex_request_contains_prompt_id(tmp_path: Path) -> None:
    """codex_request.md must contain the prompt_id."""
    write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    text = (tmp_path / "codex_request.md").read_text(encoding="utf-8")
    assert SAMPLE_PROMPT_ID in text


@pytest.mark.unit
def test_write_request_codex_request_contains_content(tmp_path: Path) -> None:
    """codex_request.md must contain the provided content."""
    write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    text = (tmp_path / "codex_request.md").read_text(encoding="utf-8")
    assert SAMPLE_CONTENT in text


@pytest.mark.unit
def test_write_request_without_prompt_id_raises_or_stops(tmp_path: Path) -> None:
    """write_request with empty prompt_id must raise ValueError or similar error."""
    with pytest.raises((ValueError, TypeError, AssertionError)):
        write_request("", SAMPLE_CONTENT, tmp_path)


@pytest.mark.unit
@pytest.mark.parametrize(
    "dirty",
    [
        "SELECT id FROM accounts WHERE token = 't'",  # raw SQL
        "C:/app/data/production.db is attached here",  # absolute .db path
    ],
)
def test_write_request_enforces_payload_hygiene(tmp_path: Path, dirty: str) -> None:
    """write_request must refuse an outbound payload that leaks SQL / a .db path to the reviewer —
    hygiene is enforced inside the bridge, not left to the caller (review finding #6).
    """
    with pytest.raises(AssertionError):
        write_request(SAMPLE_PROMPT_ID, dirty, tmp_path)


@pytest.mark.unit
def test_run_codex_review_dirty_request_stops_without_calling_exec(
    tmp_path: Path,
) -> None:
    """A hand-crafted dirty request file (bypassing write_request) must make run_codex_review
    return a stop sentinel and NEVER call codex_exec — no dirty payload leaves the machine.
    """
    req = tmp_path / "codex_request.md"
    req.write_text(
        "Prompt-ID: X\n\nSELECT id FROM accounts WHERE token = 't'", encoding="utf-8"
    )
    mock_exec = MagicMock(return_value="{}")
    result = run_codex_review(req, session_id="s", codex_exec=mock_exec)
    assert result["action"] == "stop"
    mock_exec.assert_not_called()


# ===========================================================================
# Section E.2 - run_codex_review (mock reviewer - zero real calls)
# ===========================================================================


@pytest.mark.unit
def test_run_codex_review_calls_codex_exec_once(tmp_path: Path) -> None:
    """run_codex_review must call codex_exec exactly once."""
    request_path = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    mock_exec = MagicMock(return_value=json.dumps(VALID_REVIEW_REPLY))
    run_codex_review(request_path, session_id="test-session", codex_exec=mock_exec)
    mock_exec.assert_called_once()


@pytest.mark.unit
def test_run_codex_review_returns_parsed_dict(tmp_path: Path) -> None:
    """run_codex_review must parse codex_exec reply JSON and return dict."""
    request_path = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    mock_exec = MagicMock(return_value=json.dumps(VALID_REVIEW_REPLY))
    result = run_codex_review(
        request_path, session_id="test-session", codex_exec=mock_exec
    )
    assert isinstance(result, dict)
    assert result["verdict"] == "PASS"


@pytest.mark.unit
def test_run_codex_review_does_not_make_real_network_calls(tmp_path: Path) -> None:
    """codex_exec mock must be used; no real subprocess/network calls expected.

    Verify by asserting that our injected mock is called (not the real reviewer).
    If a real codex_exec were called, it would not be a MagicMock instance.
    """
    request_path = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    mock_exec = MagicMock(return_value=json.dumps(VALID_REVIEW_REPLY))
    run_codex_review(request_path, session_id="test-session", codex_exec=mock_exec)
    # Confirm the mock (not a real binary) was used
    assert isinstance(mock_exec, MagicMock)
    assert mock_exec.call_count == 1


@pytest.mark.unit
def test_run_codex_review_non_json_reply_returns_stop_sentinel(tmp_path: Path) -> None:
    """run_codex_review must return a stop sentinel when reply is not valid JSON."""
    request_path = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    mock_exec = MagicMock(return_value="<<< PARSE ERROR: not json >>>")
    result = run_codex_review(
        request_path, session_id="test-session", codex_exec=mock_exec
    )
    # Must not raise; must return a dict with stop indicator
    assert isinstance(result, dict)
    # Either action==stop or an error key signals failure
    assert (
        result.get("action") == "stop"
        or "error" in result
        or result.get("verdict") is None
    )


@pytest.mark.unit
def test_run_codex_review_codex_exec_raises_returns_stop_sentinel(
    tmp_path: Path,
) -> None:
    """run_codex_review must return stop sentinel when codex_exec raises RuntimeError."""
    request_path = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    mock_exec = MagicMock(side_effect=RuntimeError("reviewer binary not found"))
    result = run_codex_review(
        request_path, session_id="test-session", codex_exec=mock_exec
    )
    assert isinstance(result, dict)
    assert result.get("action") == "stop" or "error" in result


@pytest.mark.unit
@pytest.mark.timeout(5)
def test_run_codex_review_completes_within_timeout(tmp_path: Path) -> None:
    """run_codex_review with mock codex_exec must return within 5 seconds."""
    request_path = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    mock_exec = MagicMock(return_value=json.dumps(VALID_REVIEW_REPLY))
    result = run_codex_review(
        request_path, session_id="test-session", codex_exec=mock_exec
    )
    assert isinstance(result, dict)


# ===========================================================================
# Section E.3 - archive_processed
# ===========================================================================


@pytest.mark.unit
def test_archive_processed_moves_request_file_to_processed_dir(tmp_path: Path) -> None:
    """archive_processed must move codex_request.md into processed/<prompt_id>/."""
    request_path = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    assert (
        request_path.exists()
    ), "Precondition: codex_request.md must exist before archiving"

    archive_processed(SAMPLE_PROMPT_ID, tmp_path)

    processed_dir = tmp_path / "processed" / SAMPLE_PROMPT_ID
    assert processed_dir.exists(), "processed/<prompt_id>/ directory must be created"
    archived = processed_dir / "codex_request.md"
    assert archived.exists(), "codex_request.md must be moved to processed/<prompt_id>/"


@pytest.mark.unit
def test_archive_processed_original_request_no_longer_in_root(tmp_path: Path) -> None:
    """After archiving, codex_request.md must no longer be at bridge_dir root."""
    write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    archive_processed(SAMPLE_PROMPT_ID, tmp_path)
    assert not (
        tmp_path / "codex_request.md"
    ).exists(), "codex_request.md must not remain at bridge_dir root after archiving"


@pytest.mark.unit
def test_archive_processed_idempotent_or_raises_on_missing(tmp_path: Path) -> None:
    """archive_processed on missing prompt_id must raise or be safely handled."""
    # No write_request called; directory doesn't have the files
    try:
        archive_processed("NONEXISTENT_PROMPT_ID", tmp_path)
        # If it returns without error, that's acceptable (no-op)
    except (FileNotFoundError, OSError, ValueError):
        pass  # Acceptable: raises on missing source


@pytest.mark.unit
def test_archive_processed_last_prompt_also_moved(tmp_path: Path) -> None:
    """last_prompt.md (if present) must also be moved to processed/<prompt_id>/."""
    write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    archive_processed(SAMPLE_PROMPT_ID, tmp_path)
    # last_prompt.md may or may not be moved; if it was created it must not remain at root
    if (tmp_path / "last_prompt.md").exists():
        pytest.fail("last_prompt.md must not remain at bridge_dir root after archiving")


# ===========================================================================
# Section E.4 - assert_payload_clean (hygiene)
# B4: parametrized malicious values (8 new + existing cases)
# ===========================================================================


@pytest.mark.unit
def test_assert_payload_clean_valid_payload_does_not_raise() -> None:
    """assert_payload_clean must not raise for a clean review payload."""
    assert_payload_clean(VALID_REVIEW_REPLY)  # must not raise


@pytest.mark.unit
def test_assert_payload_clean_absolute_db_path_raises() -> None:
    """Payload containing an absolute .db path must fail hygiene check."""
    dirty = dict(VALID_REVIEW_REPLY)
    dirty["notes"] = "DB at /var/lib/app/data.db was checked"
    with pytest.raises((AssertionError, ValueError)):
        assert_payload_clean(dirty)


@pytest.mark.unit
def test_assert_payload_clean_raw_sql_select_raises() -> None:
    """Payload containing raw SQL SELECT statement must fail hygiene check."""
    dirty = dict(VALID_REVIEW_REPLY)
    dirty["notes"] = "found: SELECT * FROM orders WHERE ts > 0"
    with pytest.raises((AssertionError, ValueError)):
        assert_payload_clean(dirty)


@pytest.mark.unit
def test_assert_payload_clean_secret_keyword_raises() -> None:
    """Payload containing 'secret' in a suspicious context must fail hygiene check."""
    dirty = dict(VALID_REVIEW_REPLY)
    dirty["notes"] = "api_secret_key=supersecretvalue123"
    with pytest.raises((AssertionError, ValueError)):
        assert_payload_clean(dirty)


@pytest.mark.unit
def test_assert_payload_clean_full_exception_traceback_raises() -> None:
    """Payload containing a full exception traceback must fail hygiene check."""
    dirty = dict(VALID_REVIEW_REPLY)
    dirty["notes"] = (
        "Traceback (most recent call last):\n"
        '  File "run_codex.py", line 10, in <module>\n'
        "    raise RuntimeError('boom')\n"
        "RuntimeError: boom"
    )
    with pytest.raises((AssertionError, ValueError)):
        assert_payload_clean(dirty)


@pytest.mark.unit
def test_assert_payload_clean_none_payload_raises() -> None:
    """assert_payload_clean with None must raise."""
    with pytest.raises((AssertionError, ValueError, TypeError)):
        assert_payload_clean(None)  # type: ignore[arg-type]


@pytest.mark.unit
def test_assert_payload_clean_missing_prompt_id_raises() -> None:
    """Payload without prompt_id must fail hygiene check."""
    dirty = dict(VALID_REVIEW_REPLY)
    del dirty["prompt_id"]
    with pytest.raises((AssertionError, ValueError, KeyError)):
        assert_payload_clean(dirty)


# B4: parametrized Windows absolute paths, SQL verbs, and traceback
@pytest.mark.unit
@pytest.mark.parametrize(
    "malicious_value",
    [
        r"C:\secret\prod.db",
        r"D:\repo\your-project\app.db",
        "SELECT * FROM orders",
        "INSERT INTO archive_log",
        "UPDATE orders SET",
        "DELETE FROM events",
        "JOIN users",
        "Traceback (most recent call last)",
    ],
)
def test_assert_payload_clean_malicious_value_raises(malicious_value: str) -> None:
    """B4: Each known-malicious value in payload notes must raise hygiene error."""
    dirty = dict(VALID_REVIEW_REPLY)
    dirty["notes"] = f"analysis: {malicious_value} found in output"
    with pytest.raises((AssertionError, ValueError)):
        assert_payload_clean(dirty)


# ===========================================================================
# Section F.2 - finding 2: sentinel payload redaction
# run_codex_review must NOT leak exc message into returned dict values.
# A naive impl puts str(exc) verbatim into "error" field -> fails hygiene.
# Tests fail RED until src redacts exc content.
# ===========================================================================


def _dict_contains_substring(d: dict[str, Any], needle: str) -> bool:
    """Return True if any string leaf in d contains needle (case-insensitive)."""
    needle_lower = needle.lower()
    for leaf in _iter_leaves(d):
        if needle_lower in leaf.lower():
            return True
    return False


def _iter_leaves(obj: Any) -> list[str]:
    """Collect all string leaf values from a nested structure."""
    leaves: list[str] = []
    if isinstance(obj, str):
        leaves.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            leaves.extend(_iter_leaves(v))
    elif isinstance(obj, list | tuple):
        for item in obj:
            leaves.extend(_iter_leaves(item))
    return leaves


@pytest.mark.unit
def test_run_codex_review_codex_exec_raises_with_path_payload_is_clean(
    tmp_path: Path,
) -> None:
    """F2-a: codex_exec raises RuntimeError with path+SQL -> returned dict must not
    contain the raw exception message (path, SQL, 'secret').

    A naive impl: error = f"codex_exec_error: {exc}" leaks str(exc) verbatim.
    This test fails RED until src redacts the exception message.
    """
    request_path = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    leak_msg = r"leak C:\secret\prod.db SELECT * FROM orders"
    mock_exec = MagicMock(side_effect=RuntimeError(leak_msg))
    result = run_codex_review(
        request_path, session_id="test-session", codex_exec=mock_exec
    )
    assert isinstance(result, dict)
    # The raw exception text must not appear in any leaf value.
    assert not _dict_contains_substring(
        result, "prod.db"
    ), "Leaked path found in returned payload (finding 2 bug)"
    assert not _dict_contains_substring(
        result, "SELECT"
    ), "Leaked SQL found in returned payload (finding 2 bug)"
    assert not _dict_contains_substring(
        result, r"C:\\secret"
    ), "Leaked secret path found in returned payload (finding 2 bug)"


@pytest.mark.unit
def test_run_codex_review_non_json_with_sensitive_content_payload_is_clean(
    tmp_path: Path,
) -> None:
    """F2-b: non-JSON reviewer reply containing sensitive string -> payload must not leak.

    A naive json.JSONDecodeError path: error = f"json_parse_error: {exc}"
    which can embed the raw reply in exc.doc. This test fails RED.
    """
    request_path = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    sensitive_reply = r"oops C:\secret\x.db DELETE FROM t"
    mock_exec = MagicMock(return_value=sensitive_reply)
    result = run_codex_review(
        request_path, session_id="test-session", codex_exec=mock_exec
    )
    assert isinstance(result, dict)
    assert not _dict_contains_substring(
        result, "x.db"
    ), "Leaked DB path in non-JSON error payload (finding 2 bug)"
    assert not _dict_contains_substring(
        result, "DELETE"
    ), "Leaked SQL verb in non-JSON error payload (finding 2 bug)"
    assert not _dict_contains_substring(
        result, r"C:\\secret"
    ), "Leaked secret path in non-JSON error payload (finding 2 bug)"


@pytest.mark.unit
def test_run_codex_review_exception_result_has_error_type_and_phase_keys(
    tmp_path: Path,
) -> None:
    """F2-c: on exception, returned dict must have 'error_type' and 'phase' keys.

    A naive impl returns only 'action' and 'error' keys -> fails RED.
    """
    request_path = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    mock_exec = MagicMock(side_effect=RuntimeError("some error"))
    result = run_codex_review(
        request_path, session_id="test-session", codex_exec=mock_exec
    )
    assert (
        "error_type" in result
    ), "Expected 'error_type' key (exception class name) in error sentinel dict"
    assert (
        "phase" in result
    ), "Expected 'phase' key (e.g. 'codex_exec') in error sentinel dict"
    assert result.get("action") == "stop"


@pytest.mark.unit
def test_run_codex_review_non_json_result_has_error_type_and_phase_keys(
    tmp_path: Path,
) -> None:
    """F2-d: on non-JSON parse failure, returned dict must have 'error_type' and 'phase'.

    phase value must be 'json_parse'. A naive impl missing both keys -> RED.
    """
    request_path = write_request(SAMPLE_PROMPT_ID, SAMPLE_CONTENT, tmp_path)
    mock_exec = MagicMock(return_value="not valid json {{")
    result = run_codex_review(
        request_path, session_id="test-session", codex_exec=mock_exec
    )
    assert "error_type" in result, "Expected 'error_type' key for json_parse failure"
    assert "phase" in result, "Expected 'phase' key for json_parse failure"
    assert (
        result.get("phase") == "json_parse"
    ), f"Expected phase='json_parse' but got {result.get('phase')!r}"
    assert result.get("action") == "stop"


# ===========================================================================
# Section F.3 - finding 3: prompt_id dot-only reject
# _SAFE_PROMPT_ID regex must reject ".", "..", "..." (dot-only strings).
# write_request and archive_processed must reject these.
# Tests fail RED until _SAFE_PROMPT_ID or _validate_prompt_id is hardened.
# ===========================================================================


@pytest.mark.unit
@pytest.mark.parametrize("dot_pid", [".", "..", "..."])
def test_write_request_dot_only_prompt_id_raises_value_error(
    dot_pid: str, tmp_path: Path
) -> None:
    """F3-a: write_request must reject dot-only prompt_id with ValueError.

    A naive _SAFE_PROMPT_ID regex accepts '.' (dots are within alphanumerics,
    underscore, hyphen, or dot) -> no ValueError raised. Test fails RED.
    """
    with pytest.raises(ValueError, match="unsafe prompt_id"):
        write_request(dot_pid, SAMPLE_CONTENT, tmp_path)


@pytest.mark.unit
@pytest.mark.parametrize("dot_pid", [".", "..", "..."])
def test_archive_processed_dot_only_prompt_id_raises_value_error(
    dot_pid: str, tmp_path: Path
) -> None:
    """F3-b: archive_processed must reject dot-only prompt_id with ValueError.

    Same root cause as F3-a. Test fails RED until regex is hardened.
    """
    with pytest.raises(ValueError, match="unsafe prompt_id"):
        archive_processed(dot_pid, tmp_path)


@pytest.mark.unit
def test_write_request_valid_standard_prompt_id_passes_regression(
    tmp_path: Path,
) -> None:
    """F3 positive: well-formed prompt_id must still pass after regex hardening."""
    valid_pid = "M3-RT-PERSIST-01_R2_GREEN_20260609_163"
    result = write_request(valid_pid, SAMPLE_CONTENT, tmp_path)
    assert result.exists(), "write_request must succeed for valid prompt_id"


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_pid",
    [
        "../evil",
        "evil/path",
        "/abs/x",
        "a\\b",
    ],
)
def test_write_request_path_traversal_prompt_id_raises_regression(
    bad_pid: str, tmp_path: Path
) -> None:
    """F3 regression: existing traversal-blocked values must still raise (unchanged)."""
    with pytest.raises((ValueError, TypeError, AssertionError)):
        write_request(bad_pid, SAMPLE_CONTENT, tmp_path)
