"""Write per-topic clip plan JSON and rebuild the flattened _all.json.

Both files are flat arrays of clip dicts — that's the existing shape the
renderer and dashboard already consume. The renderer reads each per-topic
file directly via spec_writer's path; _all.json is the cross-topic
flattened view that downstream tooling (preview_queue, schedule_shorts,
the dashboard) iterates.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CLIPS_PLAN_DIR = REPO_ROOT / "data" / "podcast" / "clips_plan"


def write_topic_plan(source_stem: str, specs: list[dict]) -> Path:
    """Write data/podcast/clips_plan/<source_stem>.json with the topic's clips.

    Always writes the file, even if specs is empty (an empty array is the
    correct representation of "this topic produced no clips" — downstream
    code already handles that case from old behaviors).
    """
    CLIPS_PLAN_DIR.mkdir(parents=True, exist_ok=True)
    path = CLIPS_PLAN_DIR / f"{source_stem}.json"
    path.write_text(json.dumps(specs, indent=2))
    return path


def rebuild_all_json() -> Path:
    """Walk every per-topic JSON and flatten into _all.json.

    Sorted by source_stem (which preserves episode topic order via the
    leading NN- prefix) then by start_sec.
    """
    CLIPS_PLAN_DIR.mkdir(parents=True, exist_ok=True)
    flat: list[dict] = []
    for topic_path in sorted(CLIPS_PLAN_DIR.glob("*.json")):
        if topic_path.name == "_all.json":
            continue
        try:
            data = json.loads(topic_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, list):
            continue
        flat.extend(data)

    flat.sort(key=lambda c: (c.get("source_stem", ""), c.get("start_sec", 0.0)))

    out_path = CLIPS_PLAN_DIR / "_all.json"
    out_path.write_text(json.dumps(flat, indent=2))
    return out_path
