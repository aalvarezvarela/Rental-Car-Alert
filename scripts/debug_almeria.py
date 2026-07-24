#!/usr/bin/env python3
"""Run the Almería Airport workflow locally for debugging."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from run_workflow_debug import main as run_workflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALMERIA_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "almeria_airport.yml"
HEADLESS = True


def main() -> int:
    os.chdir(PROJECT_ROOT)
    extra_args = [
        arg for arg in sys.argv[1:] if arg not in {"--headless", "--headful"}
    ]
    if "--headless" in sys.argv[1:]:
        headless = True
    elif "--headful" in sys.argv[1:]:
        headless = False
    else:
        headless = HEADLESS

    browser_mode = "--headless" if headless else "--headful"
    return run_workflow(
        [
            str(ALMERIA_WORKFLOW),
            "--job",
            "almeria_monitor",
            browser_mode,
            "--no-email",
            *extra_args,
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
