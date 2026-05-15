"""Flask backend for the clip-review editor.

Runs locally on the user's machine. Browser opens http://localhost:8765/
and sees every topic in the episode with Claude's proposals overlaid on the
transcript. User adjusts, the server auto-saves on every change. When user
hits Submit, the server writes per-topic clips_plan files in the renderer's
expected shape and drops a `.review_done` sentinel that the CLI watches for.

Required filesystem layout (all paths under one EPISODE_DIR passed at startup):

  EPISODE_DIR/
    transcripts/<stem>.json         # whisperX transcripts (with words[])
    audio/<stem>.mp4                # source audio for browser playback
    proposals/<stem>.json           # output of propose.py
    state/<stem>.json               # in-progress user edits (auto-created)
    clips_plan/<stem>.json          # final renderer-shaped output (on submit)
    .review_done                    # sentinel (on submit)
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from flask import Flask, Response, abort, jsonify, request, send_from_directory


# Mood → music volume (matches existing renderer's accepted band 0.08-0.14)
_MOOD_TO_VOLUME = {
    "chill":      0.10, "reflective": 0.10,
    "funny":      0.12, "hopeful":    0.12,
    "hype":       0.14, "heated":     0.14,
}

_PLATFORM_ALL = ["youtube_shorts", "instagram_reels", "tiktok", "facebook_reels"]


def _safe_name(name: str) -> str:
    """Allow alphanumerics, dash, underscore, dot, and SPACE. Path-traversal guard.
    Spaces are preserved because some episode stems contain spaces
    (e.g. '8-Bit Podcast May 5 2026 FULL FINAL V2_1080p')."""
    return re.sub(r"[^A-Za-z0-9._\- ]", "", name)


def _load_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def _flatten_words(transcript: dict) -> list[dict]:
    """Per-word list with start/end/text/global_index across the topic."""
    out: list[dict] = []
    idx = 0
    for seg in transcript.get("segments", []):
        for w in seg.get("words", []) or []:
            if "start" not in w or "end" not in w:
                continue
            out.append({
                "i": idx,
                "start": float(w["start"]),
                "end": float(w["end"]),
                "text": w["word"],
                "speaker": w.get("speaker") or seg.get("speaker") or None,
            })
            idx += 1
    out.sort(key=lambda w: w["start"])
    for i, w in enumerate(out):
        w["i"] = i
    return out


def _topic_meta_from_transcript(stem: str) -> dict:
    """Strip NN- and quality suffixes to recover the slug — same convention as propose.py."""
    name = stem
    if len(name) >= 3 and name[0:2].isdigit() and name[2] == "-":
        name = name[3:]
    for suffix in ("_auto_1080p", "_1080p"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return {"slug": name}


def _audio_path_for(episode_dir: Path, stem: str) -> Path | None:
    """Find the source mp4 for this stem.

    Lookup order (first hit wins):
      1. EPISODE_DIR/audio/<stem>.mp4              (review-staging convention)
      2. EPISODE_DIR/source/1080p/<stem>.mp4       (mirror of repo layout)
      3. <repo>/data/podcast/source/1080p/<stem>.mp4 (fallback for local dev)
    """
    candidates = [
        episode_dir / "audio" / f"{stem}.mp4",
        episode_dir / "source" / "1080p" / f"{stem}.mp4",
        Path(__file__).resolve().parent.parent.parent.parent
            / "data" / "podcast" / "source" / "1080p" / f"{stem}.mp4",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _list_topics(episode_dir: Path) -> list[str]:
    """Discover transcripts in the episode dir.

    Each transcript file becomes one "topic" tab in the editor — could be
    per-topic split files OR a single full-episode transcript. The user
    chooses the granularity by what they put in transcripts/.

    Skips backup files. If both per-topic AND a full-episode transcript
    exist, lists ALL of them — the editor surfaces them as separate tabs
    and the user picks which to work on.
    """
    transcripts_dir = episode_dir / "transcripts"
    if not transcripts_dir.exists():
        return []
    stems = set()
    for p in transcripts_dir.glob("*.json"):
        if p.suffix != ".json":
            continue
        if p.name.endswith(".pre-realign.bak") or p.name.endswith(".bak.json"):
            continue
        stems.add(p.stem)
    return sorted(stems)


def _vibe_to_volume(vibe: str) -> float:
    return _MOOD_TO_VOLUME.get(vibe, 0.12)


def _build_app(episode_dir: Path, episode_name: str) -> Flask:
    app = Flask(
        __name__,
        static_folder=str(Path(__file__).resolve().parent / "static"),
        static_url_path="/static",
    )

    transcripts_dir = episode_dir / "transcripts"
    proposals_dir = episode_dir / "proposals"
    state_dir = episode_dir / "state"
    plan_dir = episode_dir / "clips_plan"
    sentinel = episode_dir / ".review_done"
    state_dir.mkdir(parents=True, exist_ok=True)

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/episode")
    def api_episode():
        topics = []
        for stem in _list_topics(episode_dir):
            tx = _load_json(transcripts_dir / f"{stem}.json", default={})
            words = _flatten_words(tx)
            duration = float(tx.get("duration_sec") or
                             max((w["end"] for w in words), default=0.0))
            proposals = _load_json(proposals_dir / f"{stem}.json", default={"proposals": []})
            state = _load_json(state_dir / f"{stem}.json", default=None)

            # Initialize state from proposals on first visit
            if state is None:
                clips = []
                for p in proposals.get("proposals", []):
                    clips.append({
                        "id": p["id"],
                        "title": p.get("suggested_title", ""),
                        "start_sec": p["start_sec"],
                        "end_sec": p["end_sec"],
                        "vibe": p.get("vibe", "reflective"),
                        "approved": True,
                        "why": p.get("why", ""),
                        "from_proposal": True,
                    })
                state = {"clips": clips, "saved_at": None}
                _atomic_write(state_dir / f"{stem}.json", state)

            audio_path = _audio_path_for(episode_dir, stem)
            topics.append({
                "stem": stem,
                "slug": _topic_meta_from_transcript(stem)["slug"],
                "title_hint": proposals.get("title_hint", ""),
                "thesis": proposals.get("thesis", ""),
                "duration_sec": duration,
                "audio_url": f"/audio/{stem}" if audio_path else None,
                "audio_present": audio_path is not None,
                "words": words,
                "proposals": proposals.get("proposals", []),
                "clips": state["clips"],
                "saved_at": state.get("saved_at"),
            })

        return jsonify({
            "episode": episode_name,
            "episode_dir": str(episode_dir),
            "topics": topics,
            "submitted": sentinel.exists(),
        })

    @app.route("/api/save/<stem>", methods=["POST"])
    def api_save(stem):
        stem = _safe_name(stem)
        body = request.get_json(force=True) or {}
        clips = body.get("clips")
        if not isinstance(clips, list):
            return jsonify({"error": "clips must be a list"}), 400
        # Light schema enforcement (no editorial validation here — that's the user's job)
        cleaned = []
        for c in clips:
            try:
                cleaned.append({
                    "id": str(c.get("id") or f"c{len(cleaned)+1}"),
                    "title": str(c.get("title", ""))[:80],
                    "start_sec": float(c["start_sec"]),
                    "end_sec": float(c["end_sec"]),
                    "vibe": str(c.get("vibe", "reflective")),
                    "approved": bool(c.get("approved", True)),
                    "why": str(c.get("why", ""))[:500],
                    "from_proposal": bool(c.get("from_proposal", False)),
                })
            except (KeyError, TypeError, ValueError):
                continue
        state = {
            "clips": cleaned,
            "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        _atomic_write(state_dir / f"{stem}.json", state)
        return jsonify({"ok": True, "saved_at": state["saved_at"], "count": len(cleaned)})

    @app.route("/api/submit", methods=["POST"])
    def api_submit():
        """Convert state files into renderer-shaped clips_plan/<stem>.json,
        rebuild a flattened _all.json, drop the sentinel."""
        plan_dir.mkdir(parents=True, exist_ok=True)
        all_clips: list[dict] = []
        per_topic_counts: list[dict] = []

        for stem in _list_topics(episode_dir):
            state = _load_json(state_dir / f"{stem}.json", default={"clips": []})
            kept = [c for c in state.get("clips", []) if c.get("approved", True)]
            kept.sort(key=lambda c: c["start_sec"])
            specs = []
            for i, c in enumerate(kept, start=1):
                start = round(float(c["start_sec"]), 2)
                end = round(float(c["end_sec"]), 2)
                if end <= start:
                    continue
                spec = {
                    # Renderer-required (hard-indexed)
                    "clip_id":     f"{stem}_c{i}",
                    "source_stem": stem,
                    "start_sec":   start,
                    "end_sec":     end,
                    # Renderer-optional (.get-read)
                    "title":               c.get("title", ""),
                    "_audio_mood":         c.get("vibe", "reflective"),
                    "_audio_music_volume": _vibe_to_volume(c.get("vibe", "reflective")),
                    # Spec metadata
                    "duration_sec":         round(end - start, 2),
                    "platform_eligibility": [p for p in _PLATFORM_ALL]
                        if (end - start) <= 90 else ["tiktok", "instagram_reels", "youtube_shorts"],
                    "why":           c.get("why", ""),
                    "from_proposal": c.get("from_proposal", False),
                    "review_source": "human",
                    "generated_at":  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                specs.append(spec)
            _atomic_write(plan_dir / f"{stem}.json", specs)
            per_topic_counts.append({"stem": stem, "kept": len(specs)})
            all_clips.extend(specs)

        all_clips.sort(key=lambda c: (c["source_stem"], c["start_sec"]))
        _atomic_write(plan_dir / "_all.json", all_clips)

        sentinel.write_text(json.dumps({
            "submitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_clips": len(all_clips),
            "per_topic": per_topic_counts,
        }, indent=2))

        return jsonify({
            "ok": True,
            "total_clips": len(all_clips),
            "per_topic": per_topic_counts,
            "plan_dir": str(plan_dir),
        })

    @app.route("/audio/<stem>")
    def audio(stem):
        stem = _safe_name(stem)
        path = _audio_path_for(episode_dir, stem)
        if not path:
            abort(404)
        # Range-request support — important for browser <audio> seeking on big files.
        range_header = request.headers.get("Range")
        size = path.stat().st_size
        if not range_header:
            return send_from_directory(path.parent, path.name, mimetype="video/mp4")
        # Parse "bytes=START-END"
        m = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if not m:
            return send_from_directory(path.parent, path.name, mimetype="video/mp4")
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        length = end - start + 1
        with open(path, "rb") as f:
            f.seek(start)
            data = f.read(length)
        rv = Response(data, status=206, mimetype="video/mp4",
                      direct_passthrough=True)
        rv.headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        rv.headers["Accept-Ranges"] = "bytes"
        rv.headers["Content-Length"] = str(length)
        return rv

    return app


def run(episode_dir: Path, episode_name: str, host: str = "127.0.0.1", port: int = 8765):
    app = _build_app(episode_dir, episode_name)
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("episode_dir", type=str)
    p.add_argument("--episode-name", type=str, default="")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    ed = Path(args.episode_dir).resolve()
    name = args.episode_name or ed.name
    run(ed, name, args.host, args.port)
