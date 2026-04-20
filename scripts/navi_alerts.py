#!/usr/bin/env python3
"""Emit tasks to Tristan's Navi Core unified tasklist.

Any 8-bit-legacy automation error / action-required situation should call
emit_navi_task() so it shows up in Navi Core with source='8bit'.

Env:
  NAVI_URL  — base URL, default http://192.168.4.2:5055
              (pipeline container will override to http://localhost:5055)

See: ~/.claude/projects/-Users-tristanaddi1-Projects-8bit-legacy/memory/reference_navi_task_api.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

NAVI_URL = os.getenv("NAVI_URL", "http://192.168.4.2:5055")
TIMEOUT = 10

_FAILED_ALERTS_LOG = Path(
    os.getenv(
        "NAVI_FAILED_ALERTS_LOG",
        str(Path(__file__).resolve().parent.parent / "data" / "logs" / "failed-alerts.jsonl"),
    )
)


def _coerce_list(raw: Any) -> list[dict]:
    """Navi's /api/user-data endpoints return data in a few shapes. Normalize to list[dict]."""
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if isinstance(raw, dict):
        raw = raw.get("data")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return []
    if isinstance(raw, list):
        return raw
    return []


def _current_tasks() -> list[dict]:
    resp = requests.get(f"{NAVI_URL}/api/user-data/tasks/unified", timeout=TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    return _coerce_list(payload.get("data") if isinstance(payload, dict) else payload)


def _record_failure(task: dict, error: str) -> None:
    _FAILED_ALERTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _FAILED_ALERTS_LOG.open("a") as f:
        f.write(
            json.dumps({"task": task, "error": error, "at": datetime.now().astimezone().isoformat()}) + "\n"
        )


def emit_navi_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    *,
    source: str = "8bit",
) -> str | None:
    """Append a task to Navi's unified tasklist. Returns the task id on success, None on failure.

    On network failure, appends to data/logs/failed-alerts.jsonl so nothing is silently dropped —
    the next successful call can flush those.

    Task shape notes (learned the hard way 2026-04-20):
    - `text` is what Navi's Core UI renders — if it's missing, the `.replace()` call in
      core.html throws, the render loop aborts mid-iteration, and the UI freezes.
    - `type`, `done`, `dueDate` are all REQUIRED for Navi to render tasks correctly.
    - `priority` and `description` are ignored by Navi but kept here for debugging.
    """
    task = {
        "id": f"{source}-{uuid.uuid4().hex[:8]}",
        "text": title,             # Navi Core renders this — MUST be set
        "type": "task",            # vs "project" — required field
        "done": False,             # required — false = active, true = completed
        "dueDate": None,           # required (nullable) — ISO date string or null
        "source": source,
        "status": "todo",
        "priority": priority,      # ignored by Navi; useful for debugging
        "description": description, # ignored by Navi; useful for debugging
        "created": datetime.now().astimezone().isoformat(),
    }

    try:
        tasks = _current_tasks()
        tasks.append(task)
        resp = requests.post(
            f"{NAVI_URL}/api/user-data/sync",
            json={"module": "tasks", "key": "unified", "data": tasks},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return task["id"]
    except (requests.RequestException, ValueError) as exc:
        _record_failure(task, str(exc))
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a test task to Navi.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--priority", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--source", default="8bit")
    args = parser.parse_args()

    task_id = emit_navi_task(args.title, args.description, args.priority, source=args.source)
    if task_id:
        print(f"[OK] Created Navi task {task_id} — visible at {NAVI_URL}/core")
        return 0
    print(f"[FAIL] Navi unreachable — logged to {_FAILED_ALERTS_LOG}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
