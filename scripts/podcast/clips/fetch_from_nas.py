"""Pull an episode's topic transcripts + source mp4s from TrueNAS to /tmp.

Sets up the directory layout review_cli.py expects:

  /tmp/<EpisodeName_safe>/
    transcripts/<stem>.json
    audio/<stem>.mp4

Idempotent: rsync skips files already present + up-to-date. Run before
review_cli.py so the editor has audio to play locally.

Usage:
  python3 scripts/podcast/clips/fetch_from_nas.py "Episode May 5 2026"

By default, fetches every per-topic transcript (NN-slug_*_1080p.json) and
its matching mp4. Pass --pattern to override. Pass --list to print without
fetching.
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

TRUENAS_IP = os.environ.get("TRUENAS_IP", "192.168.4.2")
SSH_KEY = Path(os.environ.get("SSH_KEY", str(Path.home() / ".ssh" / "id_ed25519")))
NAS_BASE = "/mnt/pool/apps/8bit-pipeline/data/podcast"


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(shlex.quote(c) for c in cmd)}")
    return subprocess.run(cmd, check=True, **kw)


def _ssh(remote_cmd: str) -> str:
    """Run a command on the NAS via SSH; return stdout."""
    cmd = ["ssh", "-i", str(SSH_KEY), f"truenas_admin@{TRUENAS_IP}", remote_cmd]
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def _list_remote_topics(pattern: str = "[0-9][0-9]-*_1080p.json") -> list[str]:
    """List per-topic transcript stems on the NAS (no FULL episode aggregates)."""
    out = _ssh(f"ls {NAS_BASE}/transcripts/{pattern} 2>/dev/null || true")
    stems: list[str] = []
    for line in out.strip().splitlines():
        name = Path(line).name
        if name.endswith(".pre-realign.bak"):
            continue
        if name.endswith(".json"):
            stems.append(name[:-5])  # drop .json
    return sorted(set(stems))


def fetch(episode_name: str, pattern: str = "[0-9][0-9]-*_1080p.json",
          dry_run: bool = False) -> Path:
    safe = episode_name.replace(" ", "_")
    ep_dir = Path("/tmp") / safe
    transcripts_dir = ep_dir / "transcripts"
    audio_dir = ep_dir / "audio"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    stems = _list_remote_topics(pattern)
    if not stems:
        print(f"  [warn] no remote transcripts match pattern {pattern!r}")
        return ep_dir

    print(f"  [list] {len(stems)} topic(s) found:")
    for s in stems:
        print(f"    - {s}")
    if dry_run:
        return ep_dir

    # Build include list for rsync — one rsync each (transcripts + audio)
    transcripts_includes = []
    audio_includes = []
    for s in stems:
        transcripts_includes.append(f"--include={s}.json")
        audio_includes.append(f"--include={s}.mp4")

    rsync_base = [
        "rsync", "-az", "--info=progress2,name0",
        "-e", f"ssh -i {SSH_KEY}",
    ]

    print("\n  [transcripts] rsync…")
    _run(rsync_base + transcripts_includes + ["--exclude=*"] + [
        f"truenas_admin@{TRUENAS_IP}:{NAS_BASE}/transcripts/",
        f"{transcripts_dir}/",
    ])

    print("\n  [audio] rsync (this is the slow part — large mp4s)…")
    _run(rsync_base + audio_includes + ["--exclude=*"] + [
        f"truenas_admin@{TRUENAS_IP}:{NAS_BASE}/source/1080p/",
        f"{audio_dir}/",
    ])

    print(f"\n  Done. Episode dir: {ep_dir}")
    return ep_dir


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("episode", type=str, help='e.g. "Episode May 5 2026"')
    p.add_argument("--pattern", default="[0-9][0-9]-*_1080p.json",
                   help="Glob for remote transcripts. Default skips FULL aggregates.")
    p.add_argument("--list", action="store_true", help="List only, don't fetch.")
    args = p.parse_args()
    fetch(args.episode, pattern=args.pattern, dry_run=args.list)
    return 0


if __name__ == "__main__":
    sys.exit(main())
