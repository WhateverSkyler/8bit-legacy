#!/usr/bin/env python3
"""Generate a human-in-the-loop preview page for rendered shorts.

Default safety net (added 2026-05-11 after 3 quality crashes where the QA gates
approved unwatchable content): every clip that passes Gates 0/1/2/3/4 lands in
a preview queue. The user opens a self-contained HTML page, plays each clip,
checks ✓ to approve. Schedule_shorts.py only uploads approved clips.

Workflow:
  1. pipeline.py runs sources → transcribe → ... → render_clips
  2. THIS SCRIPT generates data/podcast/clips/<episode>/preview_queue.html
     listing every rendered clip + its gate decisions + metadata
  3. Container emits Navi task: "Episode <X> preview ready" + link to HTML
  4. User opens HTML, plays clips on phone/laptop
  5. User checks/unchecks per clip, clicks "Export approvals"
  6. Browser downloads/copies approved_clips.json
  7. User saves it next to the HTML (or pastes IDs into approve_clips CLI)
  8. schedule_shorts.py --approval-file approved_clips.json --execute uploads
     only the checked clips

Default-approved: any clip with Gate 4 APPROVE.
Default-unchecked: Gate 4 FLAG_FOR_REVIEW (user must affirmatively approve).
Excluded: anything in _rejected/ (already filtered out by render_clip's gate routing).

Usage:
  python3 scripts/podcast/preview_queue.py --episode "Episode May 5 2026"
  python3 scripts/podcast/preview_queue.py --episode "..." --auto-approve  # skip preview, default-approve everything (use only when trust established)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent.parent
CLIPS_DIR = ROOT / "data" / "podcast" / "clips"
CLIPS_PLAN_ALL = ROOT / "data" / "podcast" / "clips_plan" / "_all.json"
QA_LOGS = ROOT / "data" / "podcast" / "qa_logs"

ET = ZoneInfo("America/New_York")
SLOT_HOURS = [9, 13, 19]


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip().replace(" ", "_")


def _video_duration_sec(path: Path) -> float:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            timeout=10,
        ).decode().strip()
        return float(out)
    except Exception:
        return 0.0


def _gate_decisions(source_stem: str, clip_id: str) -> dict:
    """Pull the latest verdict for each gate from qa_logs/<source_stem>.jsonl.

    Returns: {"gate0": ..., "gate1": ..., "gate2": ..., "gate3": ..., "gate4": ..., "title_audit": ..., "hashtag_gen": ..., "audio_mood": ...}
    """
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_stem)
    path = QA_LOGS / f"{safe}.jsonl"
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    try:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("clip_id") == clip_id:
                gate = rec.get("gate", "?")
                # latest entry wins for each gate name
                out[gate] = rec.get("verdict", {})
    except Exception:
        pass
    return out


def _gate4_summary(verdicts: dict) -> tuple[str, str, str]:
    """Return (color_class, decision, reason) for the Gate-4 verdict."""
    g4 = verdicts.get("gate4") or {}
    decision = (g4.get("final_decision") or "").upper()
    reason = g4.get("reason", "") or ""
    if decision == "APPROVE":
        return ("approve", "APPROVE", reason)
    if decision == "FLAG_FOR_REVIEW":
        return ("flag", "FLAG_FOR_REVIEW", reason)
    if decision == "REJECT":
        return ("reject", "REJECT", reason)
    # Missing Gate 4 (skipped for short clips, or gate failed) → default to flag
    return ("missing", "no Gate 4 result", "")


def _approval_default(g4_class: str) -> bool:
    """Default approval state for the HTML checkbox.
    APPROVE → checked
    FLAG_FOR_REVIEW → UNchecked (user must affirmatively approve)
    REJECT → not displayed (already in _rejected/)
    Missing → UNchecked
    """
    return g4_class == "approve"


def _slot_schedule(n: int, start_date: str) -> list[str]:
    """Map N clips to the standard 9/13/19 ET schedule starting from start_date.
    Returns a parallel list of human-readable times."""
    if not start_date:
        return ["—"] * n
    start = datetime.fromisoformat(start_date).replace(tzinfo=ET)
    out: list[str] = []
    day = 0
    slot = 0
    while len(out) < n:
        dt = start.replace(hour=SLOT_HOURS[slot], minute=0, second=0, microsecond=0) + timedelta(days=day)
        out.append(dt.strftime("%a %m/%d  %-I:%M %p ET"))
        slot += 1
        if slot >= len(SLOT_HOURS):
            slot = 0
            day += 1
    return out


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{episode_title} — Preview Queue</title>
<style>
  :root {{
    --bg:#0e0e10; --fg:#eee; --muted:#999; --panel:#19191c; --border:#2a2a2f;
    --approve:#3aab5b; --approve-light:#4ec973;
    --flag:#e89c2b; --flag-light:#f3b658;
    --reject:#d24747; --orange:#ff9526;
  }}
  *{{box-sizing:border-box;}}
  body{{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,Helvetica,Arial,sans-serif;line-height:1.4;}}
  header{{position:sticky;top:0;z-index:10;background:#000;padding:14px 20px;border-bottom:1px solid var(--border);}}
  h1{{margin:0 0 4px;font-size:18px;}}
  .meta{{color:var(--muted);font-size:12px;}}
  .controls{{display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;}}
  button{{background:var(--orange);color:#000;border:0;padding:8px 14px;border-radius:6px;font-weight:600;cursor:pointer;font-size:13px;}}
  button.secondary{{background:#222;color:#ccc;border:1px solid var(--border);}}
  button:hover{{filter:brightness(1.1);}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:18px;padding:18px;}}
  .clip{{background:var(--panel);border:2px solid var(--border);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;}}
  .clip.approved{{border-color:var(--approve);}}
  .clip.gate-approve{{border-left:4px solid var(--approve);}}
  .clip.gate-flag{{border-left:4px solid var(--flag);}}
  .clip.gate-reject,.clip.gate-missing{{border-left:4px solid var(--reject);}}
  .clip-header{{display:flex;align-items:center;gap:10px;padding:10px 14px;background:#000;}}
  .clip-header label{{display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;font-weight:600;}}
  .clip-header input[type=checkbox]{{width:20px;height:20px;cursor:pointer;}}
  .clip-id{{font-family:monospace;font-size:11px;color:var(--muted);margin-left:auto;}}
  video{{width:100%;background:#000;aspect-ratio:9/16;max-height:560px;}}
  .info{{padding:10px 14px;font-size:13px;}}
  .info h3{{margin:0 0 6px;font-size:15px;font-weight:700;}}
  .info .hook{{color:var(--muted);margin:4px 0 8px;font-style:italic;}}
  .info .row{{margin:6px 0;font-size:12px;color:#ccc;}}
  .info .row strong{{color:var(--fg);font-weight:600;}}
  .badges{{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0;}}
  .badge{{padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600;}}
  .badge.approve{{background:var(--approve);color:#000;}}
  .badge.flag{{background:var(--flag);color:#000;}}
  .badge.reject{{background:var(--reject);color:#fff;}}
  .badge.missing{{background:#444;color:#ccc;}}
  .gate-reasons{{margin-top:6px;font-size:11px;color:var(--muted);max-height:90px;overflow:auto;padding:6px;background:#000;border-radius:4px;}}
  .footer{{padding:24px 20px;border-top:1px solid var(--border);background:#000;}}
  pre.export{{background:#0a0a0a;border:1px solid var(--border);border-radius:6px;padding:12px;color:#ccc;font-size:12px;overflow-x:auto;max-height:200px;}}
  .help{{color:var(--muted);font-size:13px;margin:8px 0;}}
  code{{background:#000;padding:2px 6px;border-radius:3px;font-size:12px;}}
  .counter{{position:fixed;bottom:18px;right:18px;background:var(--orange);color:#000;padding:10px 16px;border-radius:99px;font-weight:700;box-shadow:0 4px 14px rgba(0,0,0,.5);font-size:14px;z-index:20;}}
  .hashtags{{font-size:11px;color:#88a;word-break:break-word;}}
</style>
</head>
<body>
<header>
  <h1>📺 {episode_title} — Preview Queue</h1>
  <div class="meta">
    {n_total} rendered clip(s) · {n_default_approved} default-approved (Gate 4 APPROVE) · {n_default_flagged} flagged for review
    · generated {generated_at}
  </div>
  <div class="controls">
    <button onclick="exportApprovals()">📋 Export approved clip IDs</button>
    <button class="secondary" onclick="checkAll(true)">✓ Approve all</button>
    <button class="secondary" onclick="checkAll(false)">✗ Reject all</button>
    <button class="secondary" onclick="resetToDefaults()">↺ Reset to gate defaults</button>
  </div>
</header>

<div class="grid">
{clip_cards}
</div>

<div class="footer">
  <h2 style="margin-top:0;">When you're done:</h2>
  <p class="help">Click <strong>Export approved clip IDs</strong> above. The JSON file downloads. Save it as:</p>
  <pre class="export">data/podcast/clips/{episode_safe}/approved_clips.json</pre>
  <p class="help">Then run from the repo root on your Mac (or via TrueNAS-Tier-2 cronjob for container):</p>
  <pre class="export">python3 scripts/podcast/schedule_shorts.py --episode "{episode_title}" --start-date YYYY-MM-DD --approval-file data/podcast/clips/{episode_safe}/approved_clips.json --execute</pre>
  <p class="help">Or use the auto-approval script after this preview becomes routine:</p>
  <pre class="export">python3 scripts/podcast/approve_clips.py --episode "{episode_title}" --auto-approve   # accept all Gate 4 APPROVE clips automatically</pre>
</div>

<div class="counter" id="counter">— approved</div>

<script>
const CLIP_IDS = {clip_ids_json};

function updateCounter() {{
  const checked = document.querySelectorAll('.clip input[type=checkbox]:checked').length;
  document.getElementById('counter').textContent = `${{checked}}/${{CLIP_IDS.length}} approved`;
  document.querySelectorAll('.clip').forEach(div => {{
    const cb = div.querySelector('input[type=checkbox]');
    div.classList.toggle('approved', cb.checked);
  }});
}}

function checkAll(state) {{
  document.querySelectorAll('.clip input[type=checkbox]').forEach(cb => cb.checked = state);
  updateCounter();
}}

function resetToDefaults() {{
  document.querySelectorAll('.clip').forEach(div => {{
    const cb = div.querySelector('input[type=checkbox]');
    const defaultState = div.dataset.default === 'true';
    cb.checked = defaultState;
  }});
  updateCounter();
}}

function exportApprovals() {{
  const approved = [];
  document.querySelectorAll('.clip').forEach(div => {{
    const cb = div.querySelector('input[type=checkbox]');
    if (cb.checked) approved.push(div.dataset.clipId);
  }});
  const blob = new Blob([JSON.stringify(approved, null, 2)], {{type: 'application/json'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'approved_clips.json';
  a.click();
  URL.revokeObjectURL(url);
  // Also copy to clipboard for convenience
  navigator.clipboard.writeText(JSON.stringify(approved, null, 2)).catch(()=>{{}});
  alert(`Exported ${{approved.length}} approved clip IDs.\\n\\nSaved as approved_clips.json (also copied to clipboard).\\n\\nMove it to: data/podcast/clips/{episode_safe}/approved_clips.json`);
}}

document.addEventListener('change', e => {{
  if (e.target.matches('input[type=checkbox]')) updateCounter();
}});
updateCounter();
</script>
</body>
</html>
"""


def _format_clip_card(clip_id: str, mp4_rel: str, spec: dict, verdicts: dict,
                     scheduled_time: str, default_approved: bool) -> str:
    title = spec.get("title", clip_id)
    hook = spec.get("hook", "")
    duration = _video_duration_sec(ROOT / mp4_rel.lstrip("./")) if (ROOT / mp4_rel.lstrip("./")).exists() else 0
    hashtags = " ".join(spec.get("_llm_hashtags") or []) or "(generic from topics)"
    g4_class, g4_decision, g4_reason = _gate4_summary(verdicts)

    # Per-gate reasons (compact)
    gate_lines: list[str] = []
    for gate in ("gate1", "gate2", "gate3", "gate4"):
        v = verdicts.get(gate)
        if not v:
            continue
        if gate == "gate1":
            rec = v.get("decision", "?")
        elif gate == "gate2":
            rec = f"{v.get('sync_quality', '?')}/{v.get('recommendation', '?')}"
        elif gate == "gate3":
            rec = f"{v.get('overall_quality', '?')}/{v.get('recommendation', '?')}"
        else:  # gate4
            rec = v.get("final_decision", "?")
        reason = (v.get("reason") or "")[:200]
        gate_lines.append(f"<strong>{gate.upper()}:</strong> {escape(rec)} — {escape(reason)}")

    # Title audit + audio mood
    title_audit = verdicts.get("title_audit") or {}
    title_audit_decision = title_audit.get("decision", "")
    audio_mood = verdicts.get("audio_mood") or {}
    mood = audio_mood.get("mood", "")

    rendered_id = escape(clip_id)
    return f"""
<div class="clip gate-{g4_class}" id="{rendered_id}" data-clip-id="{rendered_id}" data-default="{'true' if default_approved else 'false'}">
  <div class="clip-header">
    <label><input type="checkbox" {'checked' if default_approved else ''}> Approve</label>
    <span class="clip-id">{rendered_id}</span>
  </div>
  <video src="{escape(mp4_rel)}" controls preload="metadata" playsinline></video>
  <div class="info">
    <h3>{escape(title)}</h3>
    <div class="hook">{escape(hook)}</div>
    <div class="badges">
      <span class="badge {g4_class}">{escape(g4_decision)}</span>
      {f'<span class="badge missing">title:{escape(title_audit_decision)}</span>' if title_audit_decision else ''}
      {f'<span class="badge missing">mood:{escape(mood)}</span>' if mood else ''}
      <span class="badge missing">{duration:.0f}s</span>
    </div>
    <div class="row"><strong>Schedule slot:</strong> {escape(scheduled_time)}</div>
    <div class="row"><strong>Hashtags:</strong> <span class="hashtags">{escape(hashtags)}</span></div>
    {f'<div class="gate-reasons">{"<br>".join(gate_lines)}</div>' if gate_lines else ''}
  </div>
</div>
""".strip()


def generate_preview(episode: str, start_date: str | None = None,
                    output_path: Path | None = None,
                    auto_approve: bool = False) -> Path | None:
    """Generate the preview HTML for an episode.

    auto_approve=True: skip the HTML page and immediately write approved_clips.json
        containing every Gate-4-APPROVE clip. Use after trust established.
    """
    episode_safe = _safe(episode)
    episode_dir = CLIPS_DIR / episode_safe
    if not episode_dir.exists():
        print(f"[FATAL] no clips dir: {episode_dir}", file=sys.stderr)
        return None

    mp4s = sorted(episode_dir.glob("*.mp4"))
    if not mp4s:
        print(f"[FATAL] no .mp4 files in {episode_dir}", file=sys.stderr)
        return None

    plan: list[dict] = []
    if CLIPS_PLAN_ALL.exists():
        try:
            plan = json.loads(CLIPS_PLAN_ALL.read_text())
        except Exception:
            plan = []
    plan_by_id = {p["clip_id"]: p for p in plan}

    # Per-clip slot times
    slot_times = _slot_schedule(len(mp4s), start_date or "")

    # Build cards + auto-approval list
    cards: list[str] = []
    clip_ids: list[str] = []
    auto_approved_ids: list[str] = []
    n_approved = 0
    n_flagged = 0
    for i, mp4 in enumerate(mp4s):
        clip_id = mp4.stem
        spec = plan_by_id.get(clip_id, {"title": clip_id, "hook": "(no spec)", "topics": []})
        source_stem = spec.get("source_stem", "unknown")
        verdicts = _gate_decisions(source_stem, clip_id)
        g4_class, _, _ = _gate4_summary(verdicts)
        default_approved = _approval_default(g4_class)
        if default_approved:
            n_approved += 1
            auto_approved_ids.append(clip_id)
        elif g4_class == "flag":
            n_flagged += 1

        # Relative path from the HTML file's location (= the episode dir)
        mp4_rel = mp4.name
        cards.append(_format_clip_card(clip_id, mp4_rel, spec, verdicts,
                                       slot_times[i], default_approved))
        clip_ids.append(clip_id)

    if auto_approve:
        approved_path = episode_dir / "approved_clips.json"
        approved_path.write_text(json.dumps(auto_approved_ids, indent=2))
        print(f"[AUTO-APPROVED] {len(auto_approved_ids)} of {len(mp4s)} clips → {approved_path}")
        return approved_path

    html = HTML_TEMPLATE.format(
        episode_title=escape(episode),
        episode_safe=escape(episode_safe),
        n_total=len(mp4s),
        n_default_approved=n_approved,
        n_default_flagged=n_flagged,
        generated_at=datetime.now(ET).strftime("%Y-%m-%d %H:%M %Z"),
        clip_cards="\n".join(cards),
        clip_ids_json=json.dumps(clip_ids),
    )
    out = output_path or (episode_dir / "preview_queue.html")
    out.write_text(html)

    # Default-approved JSON (so schedule_shorts can run with --approval-file
    # immediately if the user is satisfied with the gate defaults). User can
    # overwrite this by exporting from the HTML.
    auto_path = episode_dir / "approved_clips.json"
    if not auto_path.exists():
        # Write the GATE-4-APPROVE defaults. User will overwrite via "Export".
        auto_path.write_text(json.dumps(auto_approved_ids, indent=2))
        print(f"[DEFAULTS] wrote default approval (Gate 4 APPROVEs only): {auto_path.name}")

    print(f"[PREVIEW] {out}")
    print(f"  · {len(mp4s)} clip(s) listed")
    print(f"  · {n_approved} default-approved (Gate 4 APPROVE)")
    print(f"  · {n_flagged} flagged for review")
    print(f"  · open the HTML to review, then export approved_clips.json")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True)
    parser.add_argument("--start-date", help="YYYY-MM-DD — used to display the schedule slot per clip")
    parser.add_argument("--output", help="Output HTML path (default: <episode_dir>/preview_queue.html)")
    parser.add_argument("--auto-approve", action="store_true",
                        help="Skip the HTML preview; immediately write approved_clips.json with every Gate-4-APPROVE clip. Use only after trust established.")
    args = parser.parse_args()

    result = generate_preview(
        args.episode, args.start_date,
        Path(args.output) if args.output else None,
        auto_approve=args.auto_approve,
    )
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
