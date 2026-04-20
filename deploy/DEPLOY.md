# 8bit-pipeline — TrueNAS Deployment Guide

**What this deploys:** The `8bit-pipeline` Docker container on your TrueNAS Scale server. Runs `drop_watcher` + periodic `buffer_scheduler` + calls into `scripts/podcast/pipeline.py` and `scripts/social/schedule_photos.py` when content is dropped on the NAS.

**Deploy pattern:** Tar source → SCP to TrueNAS → build + run via TrueNAS cronjob API. Mirrors the Navi deploy flow. Works from Mac or work laptop without Docker installed locally.

---

## One-time setup on TrueNAS

**1. Create the app directory structure:**
```bash
ssh truenas_admin@192.168.4.2
mkdir -p /mnt/pool/apps/8bit-pipeline/{config,data}
```

**2. Create `/mnt/pool/apps/8bit-pipeline/.env`** with the API keys the pipeline needs:
```bash
cat > /mnt/pool/apps/8bit-pipeline/.env <<'EOF'
# Claude (clip picking + metadata + thumbnails)
ANTHROPIC_API_KEY=sk-ant-...

# Zernio (social scheduler — IG/FB/TT/YT)
ZERNIO_API_KEY=sk_...
ZERNIO_BASE_URL=https://zernio.com/api/v1

# Navi task emitter — running on same host, use LAN IP (localhost doesn't work cross-container)
NAVI_URL=http://192.168.4.2:5055
EOF
chmod 600 /mnt/pool/apps/8bit-pipeline/.env
```

**3. Google OAuth client for YouTube uploads** — one-time:
- Go to https://console.cloud.google.com
- Create project `8bit-legacy-podcast` (or reuse an existing one with YT Data API enabled)
- APIs & Services → Library → enable **YouTube Data API v3**
- APIs & Services → Credentials → Create Credentials → **OAuth 2.0 Client ID** → Type **Desktop app**
- Download the JSON → save as `/mnt/pool/apps/8bit-pipeline/config/oauth2client.json`
- First upload will print an auth URL on container startup; visit it from a browser, approve the 8-Bit Legacy YouTube channel, paste the returned code. `/app/config/.yt_token.json` gets written and is reused from then on.

**4. Confirm the NAS drop folders exist** (created earlier in session):
```bash
ls "/mnt/pool/NAS/Media/8-Bit Legacy"
# Should show: DROP-HERE-README.md, podcast/, photos/, state/, logs/
```

---

## Deploy

From the project root on Mac (or any machine with SSH + the TrueNAS API key):
```bash
# Export TRUENAS_API_KEY once (or add to config/.env and source it)
export TRUENAS_API_KEY=$(grep TRUENAS_API_KEY config/.env | cut -d= -f2)

./deploy/deploy-to-truenas.sh
```

Script output walks through: tar → SCP → cronjob build → polling for `DEPLOY_SUCCESS` marker → docker ps status + last 20 log lines.

Full build log lives at `/tmp/8bit-pipeline-build.log` on TrueNAS if the deploy fails:
```bash
ssh truenas_admin@192.168.4.2 'cat /tmp/8bit-pipeline-build.log'
```

---

## Verify it's working

**Check the container is running:**
```bash
ssh truenas_admin@192.168.4.2 "docker ps | grep 8bit-pipeline"
```

**Follow logs:**
```bash
ssh truenas_admin@192.168.4.2 "docker logs -f 8bit-pipeline"
```

Expected log lines on a clean start:
```
drop_watcher starting — MEDIA_ROOT=/media, poll=300s, scripts=/app/scripts, buffer every 12 polls
[scan] no drops to process
```

**Force a buffer-scheduler run** (useful after first deploy to confirm Zernio integration):
```bash
ssh truenas_admin@192.168.4.2 "docker exec 8bit-pipeline python3 /app/scripts/watcher/buffer_scheduler.py"
```

**Emit a test Navi task to verify alerting plumbing in-container:**
```bash
ssh truenas_admin@192.168.4.2 "docker exec 8bit-pipeline python3 /app/scripts/navi_alerts.py --title '8bit-pipeline deployed' --description 'Smoke test from inside the container. Safe to mark complete.' --priority low"
```

---

## Day-to-day use

**Drop new podcast episode** (on your Mac or Linux, over the NAS share in Finder/Files):
```
/mnt/pool/NAS/Media/8-Bit Legacy/podcast/incoming/EP-2026-05-05/
    full.mp4
    topic-01-<slug>.mp4
    topic-02-<slug>.mp4
    ...
```
Within ~5 min the watcher picks it up. Pipeline takes ~2-4 hours (transcribe is the long pole). On success, drop moves to `archive/`, rendered shorts go to `clips-archive/`, and Zernio has everything scheduled.

**Drop photos** — just dump PNGs loose into:
```
/mnt/pool/NAS/Media/8-Bit Legacy/photos/incoming/
```
Watcher groups them within ~5 min into a dated drop + schedules 2/day to IG+FB.

**Any failure** → you get a task in Navi Core with `source='8bit'` describing what broke + where.

---

## Updating the pipeline

Same command as first deploy:
```bash
./deploy/deploy-to-truenas.sh
```

Rebuilds from latest local source, recreates the container. `/mnt/pool/apps/8bit-pipeline/data/` and the NAS drop folders are untouched.

---

## Rollback

```bash
ssh truenas_admin@192.168.4.2
cd /mnt/pool/apps/8bit-pipeline
docker compose down          # stop current pipeline
# Restart a previous image version if saved, or re-run deploy with an older git checkout
```

**Never use `docker compose down -v`** — the `-v` flag deletes the `/app/data` volume which has cached transcripts, auth tokens, and intermediate state.

---

## Troubleshooting

**Container keeps restarting:**
```bash
ssh truenas_admin@192.168.4.2 "docker logs 8bit-pipeline 2>&1 | tail -100"
```
Common: missing `.env` key, wrong path mount, expired YT OAuth token (re-auth needed).

**Pipeline failed but no Navi task appeared:**
Navi might be down. Check:
```bash
curl -s http://192.168.4.2:5055/api/market-status
```
If Navi is unreachable, the alert is in `/app/data/logs/failed-alerts.jsonl` inside the container and will get flushed on the next successful Navi call.

**Zernio rate-limited:**
Automatic — error flows to a Navi task. Reduce `BUFFER_MAX_SCHEDULE_PER_RUN` via env override in docker-compose if it keeps tripping.

**"YT OAuth expired"** Navi task:
Regenerate on TrueNAS:
```bash
ssh truenas_admin@192.168.4.2
rm /mnt/pool/apps/8bit-pipeline/config/.yt_token.json
docker restart 8bit-pipeline
docker logs -f 8bit-pipeline    # it will print a new auth URL
```
