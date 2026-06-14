[PROMPT-ID: KIT-COMMIT-GUARD_REVIEW_20260614_311]

ROLE: Independent reviewer (read-only). You are Codex. -C is mounted at the kit
repo (multi-agent-harness-loop-starter). Re-verify from first principles.

== CONTEXT ==
The kit's commit guard scripts/harness_audit_rerun.py is the PreToolUse [HARNESS]
gate (Layer C: re-runs pytest/mypy/ruff to catch claimed!=actual forgery). The
SAME guard in a downstream project was audited and 3 latent holes were found that
ALSO existed in this kit. This change fixes them in the kit + adds the missing
self-test. The kit's policy (full 6-stage Layer1, config-driven, shell=False,
multi-tool allowlist) is INTENTIONALLY preserved — only the holes are filled.

== CHANGES (git diff HEAD) ==
- scripts/harness_audit_rerun.py:
  - NEW _as_number(): coerces score; non-numeric string -> None (block). Replaces
    the `isinstance(score,(int,float)) and score<TH` bypass (a string '100%' used
    to skip the threshold check). Applied to AUDIT (audit_gate_error) + REVIEW score.
  - NEW audit_gate_error(task_id, stages): validates the LATEST AUDIT (audits[-1]),
    not the first. Closes the multi-AUDIT hole where a stale earlier pass masked a
    later fail/flag/pviol. fail->fix->pass retry (latest=pass) still passes. main()
    now calls it instead of the inline first-AUDIT block.
  - layer2_rerun_verify: after selecting the VERIFY/bundled source, if it has NO
    re-runnable command (pytest_cmd/mypy_cmd/ruff_cmd/coverage_cmd) -> block
    ("unverifiable record"). Closes the empty-VERIFY-passes-without-rerun hole.
  - Header DRIFT-FIX (C)/(D)/(E) document the above.
- tests/unit/test_commit_guard.py (NEW): pins TASK_ID_RE, verify_stage_presence,
  _as_number, audit_gate_error (latest-AUDIT + string score + retry), and
  layer2_rerun_verify (empty source, echo-forgery, real rerun match/mismatch).

== WHAT TO CHECK ==
1. audit_gate_error uses LATEST audit and preserves all invariants (status/score/
   flags/pviols). main() wiring equivalent to the old inline block (no condition lost)?
2. _as_number: blocks non-numeric, allows int/float/numeric-string/None(=0=block<TH)?
3. layer2 empty-source block does not break the existing real-rerun / forgery paths.
4. NO weakening of the kit's security-critical pieces (_is_safe_tool_cmd, shell=False
   run_cmd, the 6-stage verify_stage_presence, config loader). Those must be intact.
5. No new HIGH. Any regression to existing behavior?

== RE-RUN (claimed==actual; kit uses system python) ==
python -m pytest tests/unit/test_commit_guard.py tests/test_harness_hardening.py tests/unit/test_auto_gate.py -q
python -m mypy scripts/harness_audit_rerun.py --ignore-missing-imports --no-incremental
python -m ruff check scripts/harness_audit_rerun.py tests/unit/test_commit_guard.py
Claimed: 24 (guard) + 142 (existing) passed; mypy 0; ruff clean; black clean.
(tmp_path WinError-5 in a sandbox = environment, not a real failure — judge source.)

== REPLY FORMAT ==
verdict-id: _311
verdict: PASS | PASS-with-nits | BLOCKED
findings: [ {severity, file:line, issue} ]   (CRITICAL/HIGH block)
security_intact: (are _is_safe_tool_cmd / shell=False / 6-stage / config untouched?)
latest_audit_ok / string_score_ok / empty_source_ok:
notes:
