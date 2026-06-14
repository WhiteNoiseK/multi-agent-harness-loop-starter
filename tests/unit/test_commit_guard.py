"""Unit tests for scripts/harness_audit_rerun.py — the PreToolUse commit guard (Layer C).

WHY THIS FILE EXISTS
--------------------
The commit guard is the "last line of defense": on a `git commit ... [HARNESS]` it
re-runs pytest/mypy/ruff and compares claimed==actual to catch a forged score
record. A guard with no self-test silently rots — a partial/incomplete fix ships
unnoticed (exactly how the original task-id regex stayed broken). These tests pin
the guard's blocking logic so it can never regress unverified.

WHAT IS PINNED
--------------
- TASK_ID_RE: captures multi-segment task IDs, rejects non-IDs.
- verify_stage_presence: missing stage is reported; bundled forms are accepted.
- audit_gate_error: validates the **latest** AUDIT (a stale earlier pass must not
  mask a later fail/flag/pviol); non-numeric score is blocked.
- layer2_rerun_verify: a rerun source with no command is rejected; echo-forgery is
  rejected; a real claimed==actual rerun passes / a mismatch is reported.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# scripts/ import path — this test lives at tests/unit/, so the kit root is parents[2].
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from harness_audit_rerun import (  # noqa: E402  (scripts/ on sys.path above)
    TASK_ID_RE,
    _as_number,
    audit_gate_error,
    layer2_rerun_verify,
    verify_stage_presence,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _audit(score=100, status="pass", **extra):
    """A passing AUDIT entry, overridable via kwargs."""
    return {
        "stage": "AUDIT",
        "status": status,
        "score": score,
        "hallucination_flags": [],
        "permission_matrix_violations": [],
        "artifacts": {},
        **extra,
    }


def _tiny_test_file(tmp_path: Path, n: int = 2) -> Path:
    p = tmp_path / "_tiny_tests.py"
    p.write_text(
        "\n".join(f"def test_t{i}():\n    assert True\n" for i in range(n)),
        encoding="utf-8",
    )
    return p


def _pytest_cmd_for(test_file: Path) -> str:
    py = sys.executable.replace("\\", "/")
    return f'"{py}" -m pytest "{test_file}" -q --no-header -p no:cacheprovider'


# ── TASK_ID_RE ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "task_id",
    ["M3-RT-PERSIST-01", "M3-2x-E-FILES", "M3-PACKET-E2E-01", "M2-04", "M3-2x-A"],
)
def test_task_id_re_captures_multi_segment_ids(task_id: str) -> None:
    m = TASK_ID_RE.search(f"feat({task_id}): work [HARNESS]")
    assert m is not None and m.group(1) == task_id


@pytest.mark.parametrize("bad", ["(M-05)", "(X1-05)", "chore: foo [HARNESS]"])
def test_task_id_re_rejects_non_ids(bad: str) -> None:
    assert TASK_ID_RE.search(bad) is None


# ── verify_stage_presence ────────────────────────────────────────────────────


def test_verify_stage_presence_reports_missing() -> None:
    missing = verify_stage_presence([{"stage": "RED"}, {"stage": "AUDIT"}])
    assert set(missing) == {"GREEN", "VERIFY", "REVIEW", "FIX"}


def test_verify_stage_presence_full_six_ok() -> None:
    stages = [
        {"stage": s} for s in ("RED", "GREEN", "VERIFY", "REVIEW", "FIX", "AUDIT")
    ]
    assert verify_stage_presence(stages) == []


def test_verify_stage_presence_bundled_red_to_audit_ok() -> None:
    assert verify_stage_presence([{"stage": "RED_TO_AUDIT"}]) == []


# ── _as_number (C4 string-score bypass) ──────────────────────────────────────


def test_as_number_none_is_zero() -> None:
    assert _as_number(None) == 0.0


def test_as_number_numeric() -> None:
    assert _as_number(98) == 98.0
    assert _as_number("98") == 98.0


def test_as_number_non_numeric_is_none() -> None:
    assert _as_number("100%") is None
    assert _as_number("pass") is None


# ── audit_gate_error (HIGH-2 latest-AUDIT + C4) ──────────────────────────────


def test_audit_gate_valid_pass_is_none() -> None:
    assert audit_gate_error("M3-X", [_audit()]) is None


def test_audit_gate_missing_audit_blocks() -> None:
    assert audit_gate_error("M3-X", [{"stage": "RED"}]) is not None


def test_audit_gate_latest_flag_blocks_even_if_earlier_passed() -> None:
    """HIGH-2: a stale earlier pass must NOT mask a later flagged AUDIT."""
    stages = [_audit(), _audit(hallucination_flags=["HALLUCINATION: x"])]
    err = audit_gate_error("M3-X", stages)
    assert err is not None and "hallucination" in err.lower()


def test_audit_gate_fail_then_pass_retry_is_allowed() -> None:
    """A legitimate fail→fix→pass retry (latest = pass) must pass."""
    stages = [_audit(status="fail", score=60), _audit()]
    assert audit_gate_error("M3-X", stages) is None


def test_audit_gate_string_score_blocks() -> None:
    """C4: a non-numeric score must not skip the >= threshold check."""
    err = audit_gate_error("M3-X", [_audit(score="100%")])
    assert err is not None and "numeric" in err.lower()


def test_audit_gate_below_threshold_blocks() -> None:
    assert audit_gate_error("M3-X", [_audit(score=80)]) is not None


# ── layer2_rerun_verify (C1-class empty source + forgery + real rerun) ───────


def test_layer2_empty_verify_source_blocks(tmp_path: Path) -> None:
    """C1-class: a VERIFY stage with NO re-runnable command must not pass silently."""
    errors = layer2_rerun_verify([{"stage": "VERIFY", "artifacts": {}}], tmp_path)
    assert errors and "unverifiable record" in errors[0]


def test_layer2_cmd_without_result_blocks(tmp_path: Path) -> None:
    """Codex _311: a pytest_cmd with NO pytest_result skips its rerun and verifies
    nothing — it must be rejected, not pass silently."""
    stages = [
        {
            "stage": "VERIFY",
            "artifacts": {"pytest_cmd": _pytest_cmd_for(_tiny_test_file(tmp_path, 1))},
            # no pytest_result, no other cmd+claim pair
        }
    ]
    errors = layer2_rerun_verify(stages, tmp_path)
    assert errors and "unverifiable record" in errors[0]


def test_layer2_echo_forgery_blocks(tmp_path: Path) -> None:
    stages = [
        {
            "stage": "VERIFY",
            "artifacts": {
                "pytest_cmd": "echo 7 passed",
                "pytest_result": {"passed": 7, "failed": 0, "skipped": 0, "errors": 0},
            },
        }
    ]
    errors = layer2_rerun_verify(stages, tmp_path)
    assert errors and "forgery" in errors[0].lower()


def test_layer2_real_rerun_match_passes(tmp_path: Path) -> None:
    cmd = _pytest_cmd_for(_tiny_test_file(tmp_path, 2))
    stages = [
        {
            "stage": "VERIFY",
            "artifacts": {
                "pytest_cmd": cmd,
                "pytest_result": {"passed": 2, "failed": 0, "skipped": 0, "errors": 0},
            },
        }
    ]
    assert layer2_rerun_verify(stages, tmp_path) == []


def test_layer2_real_rerun_mismatch_blocks(tmp_path: Path) -> None:
    cmd = _pytest_cmd_for(_tiny_test_file(tmp_path, 2))
    stages = [
        {
            "stage": "VERIFY",
            "artifacts": {
                "pytest_cmd": cmd,
                "pytest_result": {"passed": 5, "failed": 0, "skipped": 0, "errors": 0},
            },
        }
    ]
    errors = layer2_rerun_verify(stages, tmp_path)
    assert any("claimed=5" in e for e in errors)
