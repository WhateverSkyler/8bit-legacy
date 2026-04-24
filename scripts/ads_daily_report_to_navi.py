#!/usr/bin/env python3
"""Run ads_daily_report.py, capture stdout, emit it as a Navi task.

Designed for unattended cron use (daily 8 AM ET via TrueNAS cronjob).
The text output of ads_daily_report.py is embedded in the Navi task
description. Priority is escalated if the report mentions a tripped
breaker or ceiling.

Usage:
  python3 scripts/ads_daily_report_to_navi.py
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from navi_alerts import emit_navi_task  # noqa: E402

REPORT_SCRIPT = ROOT / "scripts" / "ads_daily_report.py"


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(REPORT_SCRIPT)],
        capture_output=True, text=True, timeout=180,
    )
    body = (proc.stdout or "").strip()
    if proc.returncode != 0 or not body:
        body = (body or "") + "\n\n---\nSTDERR:\n" + (proc.stderr or "")

    # Escalate priority on failure signals in the body text.
    lower = body.lower()
    if "ceiling hit" in lower or "hard cap" in lower or "no campaign found" in lower:
        priority = "critical"
    elif proc.returncode != 0:
        priority = "high"
    else:
        priority = "low"

    title = f"Google Ads daily report — {date.today().isoformat()}"
    task_id = emit_navi_task(title, description=body, priority=priority)
    if task_id:
        print(f"emitted Navi task {task_id}")
        return 0
    print("FAIL: navi emission failed (check data/logs/failed-alerts.jsonl)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
