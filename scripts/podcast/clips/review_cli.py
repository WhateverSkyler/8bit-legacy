"""CLI driver for the human-in-the-loop clip review.

Usage:
  python3 scripts/podcast/clips/review_cli.py "Episode May 5 2026"

What it does:
  1. Resolves the EPISODE_DIR for the given episode.
  2. Finds topic transcripts in EPISODE_DIR/transcripts/. If proposals
     don't exist yet for any topic, runs propose.py first.
  3. Starts the Flask review server on localhost:8765.
  4. Opens the user's default browser to that URL.
  5. Blocks until EPISODE_DIR/.review_done sentinel appears
     (written by /api/submit when the user hits the Submit button).
  6. Prints a summary and exits 0 — the calling pipeline can then run
     the renderer against the per-topic clips_plan/ JSONs.

If propose.py hasn't been run yet, this script runs it first (in parallel
across topics) before opening the browser.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Make the package importable when running as a script
THIS_DIR = Path(__file__).resolve().parent
PODCAST_DIR = THIS_DIR.parent
SCRIPTS_DIR = PODCAST_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from podcast.clips import propose as propose_mod
from podcast.clips import review_server


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _resolve_episode_dir(episode_name: str, override: Path | None) -> Path:
    """Decide where the editor reads/writes files.

    Priority:
      1. --episode-dir override
      2. /tmp/<EpisodeName_safe>/  (if it exists — set up by fetch_from_nas.py)
      3. data/podcast/<EpisodeName_with_underscores>/  (if it exists — local layout)
      4. /tmp/<EpisodeName_safe>/  (created fresh, the canonical staging area)
    """
    if override:
        return override.resolve()

    safe = episode_name.replace(" ", "_")
    tmp_path = Path("/tmp") / safe
    repo_path = REPO_ROOT / "data" / "podcast" / safe

    if tmp_path.exists():
        return tmp_path
    if repo_path.exists():
        return repo_path
    tmp_path.mkdir(parents=True, exist_ok=True)
    return tmp_path


def _ensure_episode_dir_layout(ed: Path) -> None:
    """Create the subdirs the server needs, mirror transcripts/audio if found
    in the repo's canonical layout but not yet in EPISODE_DIR."""
    (ed / "transcripts").mkdir(parents=True, exist_ok=True)
    (ed / "audio").mkdir(parents=True, exist_ok=True)
    (ed / "proposals").mkdir(parents=True, exist_ok=True)
    (ed / "state").mkdir(parents=True, exist_ok=True)
    (ed / "clips_plan").mkdir(parents=True, exist_ok=True)

    # Helpful one-time mirror: if transcripts dir is empty but the repo's
    # data/podcast/transcripts/ has stuff, symlink the relevant ones.
    if not any((ed / "transcripts").glob("*.json")):
        repo_transcripts = REPO_ROOT / "data" / "podcast" / "transcripts"
        if repo_transcripts.exists():
            for src in repo_transcripts.glob("*_1080p.json"):
                if "FULL" in src.name or "Full" in src.name:
                    continue
                dst = ed / "transcripts" / src.name
                if not dst.exists():
                    try:
                        dst.symlink_to(src)
                    except OSError:
                        shutil.copy(src, dst)
            print(f"  [layout] mirrored transcripts from {repo_transcripts}")


def _list_topics_needing_proposals(ed: Path) -> list[Path]:
    """Find transcripts in this episode dir that don't yet have a proposals JSON."""
    needs: list[Path] = []
    for tx in sorted((ed / "transcripts").glob("*.json")):
        if tx.name.endswith(".pre-realign.bak") or "FULL" in tx.name:
            continue
        prop_path = ed / "proposals" / tx.name
        if not prop_path.exists():
            needs.append(tx)
    return needs


def _generate_proposals(transcripts: list[Path], proposals_dir: Path) -> None:
    """Run propose for each transcript in parallel, write to proposals_dir."""
    proposals_dir.mkdir(parents=True, exist_ok=True)

    async def _one(tx: Path):
        try:
            data = await asyncio.to_thread(propose_mod._propose_sync, tx)
        except Exception as exc:
            print(f"  [propose] {tx.stem}: FAILED — {exc}")
            return
        out = proposals_dir / f"{tx.stem}.json"
        out.write_text(json.dumps(data, indent=2))
        print(f"  [propose] {tx.stem}: {len(data['proposals'])} proposals "
              f"(${(data['tokens_in']*3 + data['tokens_out']*15)/1e6:.3f})")

    print(f"  [propose] running on {len(transcripts)} topic(s) in parallel…")
    asyncio.run(asyncio.gather(*[_one(t) for t in transcripts]))


def _free_port(host: str, preferred: int) -> int:
    """Return preferred port if free; else next available."""
    for p in [preferred] + list(range(preferred + 1, preferred + 50)):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, p))
                return p
        except OSError:
            continue
    raise RuntimeError(f"No free port near {preferred}")


def _wait_for_sentinel(sentinel: Path, server_thread: threading.Thread,
                       poll_sec: float = 1.0) -> dict:
    """Block until the user submits. Returns the sentinel's parsed contents."""
    print()
    print("  Waiting for you to finish editing in the browser…")
    print("  (the page auto-saves, so you can close + reopen anytime)")
    print()
    spinner = "|/-\\"
    sp_i = 0
    last_print = 0.0
    try:
        while not sentinel.exists():
            if not server_thread.is_alive():
                raise RuntimeError("Review server died unexpectedly")
            now = time.time()
            if now - last_print > 5.0:
                print(f"  {spinner[sp_i % 4]} still waiting… (Ctrl-C to abort review)",
                      end="\r", flush=True)
                sp_i += 1
                last_print = now
            time.sleep(poll_sec)
    except KeyboardInterrupt:
        print("\n  Aborted by user. No clips_plan written.")
        sys.exit(130)
    print("\n  Submit detected!")
    try:
        return json.loads(sentinel.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Open the clip-review editor for an episode.")
    parser.add_argument("episode", type=str, help='e.g. "Episode May 5 2026"')
    parser.add_argument("--episode-dir", type=str, default=None,
                        help="Override staging dir (default: /tmp/<EpisodeName>)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't auto-open the browser; print the URL only.")
    parser.add_argument("--skip-propose", action="store_true",
                        help="Don't run propose.py even if proposals are missing.")
    parser.add_argument("--reset", action="store_true",
                        help="Wipe state/, clips_plan/, .review_done before starting.")
    args = parser.parse_args()

    ed = _resolve_episode_dir(args.episode, Path(args.episode_dir) if args.episode_dir else None)
    print(f"Episode dir: {ed}")
    _ensure_episode_dir_layout(ed)

    if args.reset:
        for p in (ed / "state").glob("*.json"):
            p.unlink()
        for p in (ed / "clips_plan").glob("*.json"):
            p.unlink()
        sentinel = ed / ".review_done"
        if sentinel.exists():
            sentinel.unlink()
        print("  [reset] cleared state/, clips_plan/, .review_done")

    # Sentinel might already exist from a prior run — clear if so so we wait fresh
    sentinel = ed / ".review_done"
    if sentinel.exists():
        sentinel.unlink()
        print("  [reset] cleared stale .review_done from prior run")

    # Generate proposals for any topics that don't have them yet
    needs = _list_topics_needing_proposals(ed)
    if needs and not args.skip_propose:
        _generate_proposals(needs, ed / "proposals")
    elif needs:
        print(f"  [propose] skipping (--skip-propose), {len(needs)} topic(s) will show no proposals")

    # Start server
    port = _free_port("127.0.0.1", args.port)
    url = f"http://127.0.0.1:{port}/"
    print(f"  Review UI: {url}")

    server_thread = threading.Thread(
        target=review_server.run,
        kwargs={"episode_dir": ed, "episode_name": args.episode,
                "host": "127.0.0.1", "port": port},
        daemon=True,
    )
    server_thread.start()
    # Tiny pause so Flask binds the socket before we open the browser
    time.sleep(0.6)

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            print(f"  (couldn't auto-open browser; navigate to {url} yourself)")

    summary = _wait_for_sentinel(sentinel, server_thread)
    total = summary.get("total_clips", 0)
    print(f"  Reviewed plan written: {total} clips approved across "
          f"{len(summary.get('per_topic', []))} topics")
    print(f"  Per-topic JSONs: {ed / 'clips_plan'}/")
    print(f"  Flat _all.json:  {ed / 'clips_plan' / '_all.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
