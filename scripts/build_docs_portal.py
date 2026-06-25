"""Build the human-review docs portal (markdown -> HTML).

The markdown under docs/ stays the single source of truth; this script only RENDERS it to
a static site (`site/`, which is gitignored). Navigation is auto-generated, so adding a new
.md file under docs/ makes it appear in the portal with no config change.

Usage:
  python scripts/build_docs_portal.py            # refresh the Foam catalog, then build to site/
  python scripts/build_docs_portal.py --serve     # live-reload preview at http://localhost:8000
  python scripts/build_docs_portal.py --strict     # fail on warnings (broken links, etc.)

Prerequisite (one-time): pip install -r requirements-docs.txt
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> int:
    """Run a subcommand from the repo root and return its exit code."""
    return subprocess.run(cmd, cwd=_ROOT).returncode


def main() -> int:
    """Refresh the auto-catalog, then build (or serve) the MkDocs portal."""
    args = set(sys.argv[1:])

    # Keep _recent.md / _authority.md fresh so the portal's index pages are current.
    catalog = _ROOT / "scripts" / "foam_catalog.py"
    if catalog.exists():
        _run([sys.executable, str(catalog)])

    if "--serve" in args:
        return _run([sys.executable, "-m", "mkdocs", "serve"])

    cmd = [sys.executable, "-m", "mkdocs", "build"]
    if "--strict" in args:
        cmd.append(
            "--strict"
        )  # opt-in: links to repo-root files (AGENTS.md/.clauderules) live outside docs/ and would warn

    code = _run(cmd)
    if code != 0:
        print(
            "\n[hint] Is MkDocs installed?  ->  pip install -r requirements-docs.txt",
            file=sys.stderr,
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
