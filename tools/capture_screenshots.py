"""Compatibility wrapper for the authenticated, project-local screenshot audit."""
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    subprocess.run(
        ["node", str(ROOT / "scripts" / "capture_all_views.js")],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
