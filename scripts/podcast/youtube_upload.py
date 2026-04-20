#!/usr/bin/env python3
"""Upload podcast videos to YouTube with scheduled publish dates.

OAuth flow:
  - config/oauth2client.json = Google OAuth 2.0 Desktop client (user downloads from GCP)
  - config/.yt_token.json    = cached refresh token (auto-written after first auth)

Reads metadata from data/podcast/metadata/<stem>.json and thumbnail from
data/podcast/thumbnails/<stem>.jpg. Sets status.privacyStatus=private +
status.publishAt = scheduled publish time.

Usage:
  python3 scripts/podcast/youtube_upload.py <video.mp4> --publish-at "2026-04-20T18:00:00-04:00"
  python3 scripts/podcast/youtube_upload.py --batch data/podcast/source/1080p/ --schedule schedule.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_1080P = ROOT / "data" / "podcast" / "source" / "1080p"
METADATA_DIR = ROOT / "data" / "podcast" / "metadata"
THUMB_DIR = ROOT / "data" / "podcast" / "thumbnails"
CONFIG = ROOT / "config"
CLIENT_SECRETS = CONFIG / "oauth2client.json"
TOKEN_CACHE = CONFIG / ".yt_token.json"
UPLOAD_LOG = ROOT / "data" / "podcast" / "youtube_uploads.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def _get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_CACHE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_CACHE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS.exists():
                raise FileNotFoundError(
                    f"Missing {CLIENT_SECRETS}. Create GCP OAuth 2.0 Desktop client, "
                    "download JSON, save there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_CACHE.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def _load_metadata(video: Path) -> dict:
    meta_path = METADATA_DIR / f"{video.stem}.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"metadata missing: {meta_path} — run generate_metadata.py first")
    return json.loads(meta_path.read_text())


def upload_one(video: Path, publish_at: str | None, privacy: str = "private") -> dict:
    from googleapiclient.http import MediaFileUpload

    yt = _get_service()
    meta = _load_metadata(video)

    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": meta["description"],
            "tags": meta.get("tags", []),
            "categoryId": meta.get("category_id", "20"),
            "defaultLanguage": meta.get("default_language", "en"),
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    if publish_at:
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = publish_at

    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True,
                            mimetype="video/mp4")
    print(f"[UPLOAD] {video.name} ({video.stat().st_size / 1e9:.2f} GB)")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media,
                             notifySubscribers=False)

    response = None
    last_progress = -1
    while response is None:
        status, response = req.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            if pct != last_progress and pct % 10 == 0:
                print(f"  {pct}%")
                last_progress = pct

    video_id = response["id"]
    print(f"[OK] {video.name} → https://youtu.be/{video_id}  (publishAt={publish_at or 'now'})")

    thumb = THUMB_DIR / f"{video.stem}.jpg"
    if thumb.exists():
        try:
            yt.thumbnails().set(videoId=video_id, media_body=str(thumb)).execute()
            print(f"  thumbnail set")
        except Exception as exc:
            print(f"  [WARN] thumbnail set failed: {exc}")

    return {"video_id": video_id, "title": meta["title"], "publish_at": publish_at,
            "source": str(video.relative_to(ROOT))}


def _append_log(entry: dict) -> None:
    existing = []
    if UPLOAD_LOG.exists():
        try:
            existing = json.loads(UPLOAD_LOG.read_text())
        except json.JSONDecodeError:
            existing = []
    existing.append(entry)
    UPLOAD_LOG.write_text(json.dumps(existing, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?")
    parser.add_argument("--publish-at", help="RFC 3339 timestamp, e.g. 2026-04-20T18:00:00-04:00")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    parser.add_argument("--batch", help="Dir of MP4s to upload")
    parser.add_argument("--schedule", help="JSON file: {stem: iso_publish_at} for batch mode")
    args = parser.parse_args()

    schedule = {}
    if args.schedule:
        schedule = json.loads(Path(args.schedule).read_text())

    targets: list[Path] = []
    if args.video:
        targets.append(Path(args.video).resolve())
    if args.batch:
        targets.extend(sorted(Path(args.batch).resolve().glob("*.mp4")))
    if not targets:
        parser.error("pass a video path or --batch")

    for v in targets:
        try:
            pub = args.publish_at or schedule.get(v.stem)
            result = upload_one(v, pub, args.privacy)
            _append_log(result)
        except Exception as exc:
            print(f"[ERROR] {v.name}: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
