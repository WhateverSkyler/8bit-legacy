#!/usr/bin/env bash
# Run the shorts pipeline on a specific episode WITHOUT publishing.
#
# Spins up one-shot docker containers (NOT the long-running drop_watcher)
# to do: realign transcripts → pick from FULL EPISODE only with chunked
# 30-min windows → render via YuNet → generate preview HTML.
#
# Pulls the preview HTML + all rendered MP4s back to /tmp on the Mac so
# the user can review locally before approving anything to ship.
#
# Usage:
#   ./deploy/test-on-episode.sh "Episode May 5 2026"
#   ./deploy/test-on-episode.sh "Episode May 5 2026" "8-Bit Podcast May 5 2026 FULL FINAL V2"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

EPISODE="${1:?usage: $0 \"Episode May 5 2026\" [\"<full-video-stem>\"]}"
EPISODE_SAFE="$(echo "$EPISODE" | tr ' ' '_')"
FULL_TRANSCRIPT_STEM="${2:-8-Bit Podcast May 5 2026 FULL FINAL V2}"

TRUENAS_IP="${TRUENAS_IP:-192.168.4.2}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
TRUENAS_API_KEY="${TRUENAS_API_KEY:-$(grep ^TRUENAS_API_KEY "$REPO_ROOT/config/.env" 2>/dev/null | cut -d= -f2 | tr -d '"' || echo '')}"

if [[ -z "$TRUENAS_API_KEY" ]]; then
  echo "FATAL: set TRUENAS_API_KEY (or put it in config/.env)" >&2
  exit 1
fi

# ===== Build the inner script that runs INSIDE the container =====
# Single-quoted heredoc: NO outer-shell variable expansion happens. We bake
# values in via sed substitution after generating it. This avoids the
# nested-quoting nightmare that the previous version hit.
cat > /tmp/test-inner.sh <<'INNER'
#!/bin/bash
# NOTE: NO `set -e`. render_clip.py exits non-zero when ANY clip is rejected
# at Gate 2/3 — those rejections are expected and shouldn't kill the run.
# We want preview_queue.py to still generate the HTML for whatever survived.
cd /app
FULL_TRANSCRIPT="/app/data/podcast/transcripts/__STEM___1080p.json"
EPISODE="__EPISODE__"
if [ ! -f "$FULL_TRANSCRIPT" ]; then
  echo "FATAL: full transcript not found: $FULL_TRANSCRIPT"
  ls /app/data/podcast/transcripts/
  exit 1
fi
echo "--- clearing old clips_plan/*.json + old clips/Episode_May_5_2026/*.mp4 so we only get FRESH picks ---"
rm -f /app/data/podcast/clips_plan/*.json
# Wipe prior rendered clips for this episode so preview_queue only sees the new render
EPISODE_SAFE=$(echo "$EPISODE" | tr ' ' '_')
rm -f "/app/data/podcast/clips/${EPISODE_SAFE}/"*.mp4 "/app/data/podcast/clips/${EPISODE_SAFE}/"*.ass 2>/dev/null
rm -rf "/app/data/podcast/clips/${EPISODE_SAFE}/_kf" "/app/data/podcast/clips/${EPISODE_SAFE}/preview" 2>/dev/null
mkdir -p "/app/data/podcast/clips/${EPISODE_SAFE}/_rejected"
echo "--- pick_clips: FROM FULL EPISODE ONLY, chunked 30-min windows ---"
python3 scripts/podcast/pick_clips.py "$FULL_TRANSCRIPT" --chunk-minutes 30 --target-count 30
echo "--- copying picks to _all.json so render_clip.py finds them ---"
cp "/app/data/podcast/clips_plan/__STEM___1080p.json" /app/data/podcast/clips_plan/_all.json
echo "--- render_clips (rc ignored — Gate-2/3 rejects are expected) ---"
python3 scripts/podcast/render_clip.py --batch /app/data/podcast/clips_plan/_all.json --episode "$EPISODE" || true
echo "--- preview_queue ---"
START_DATE=$(date -d "+1 day" +%Y-%m-%d 2>/dev/null || date -v+1d +%Y-%m-%d)
python3 scripts/podcast/preview_queue.py --episode "$EPISODE" --start-date "$START_DATE"
INNER

# Substitute placeholders with sed (handles spaces/special chars safely)
sed -i.bak "s|__STEM__|${FULL_TRANSCRIPT_STEM}|g; s|__EPISODE__|${EPISODE}|g" /tmp/test-inner.sh
rm -f /tmp/test-inner.sh.bak
chmod +x /tmp/test-inner.sh

# ===== Build the outer wrapper that runs as ROOT on TrueNAS =====
cat > /tmp/test-outer.sh <<OUTER
#!/bin/bash
{
  echo "===== EPISODE: $EPISODE ====="
  echo "===== \$(date) ====="
  echo

  echo "==> [1/4] Stop any running 8bit-pipeline (so we own /app/data exclusively)"
  docker stop 8bit-pipeline 2>/dev/null || true
  sleep 2

  echo "==> [2/4] Re-align transcripts via whisperX (refines word timing to ±50ms)"
  docker run --rm --name 8bit-test-realign \\
    -v /mnt/pool/apps/8bit-pipeline/data:/app/data \\
    -v /mnt/pool/apps/8bit-pipeline/config:/app/config \\
    -v "/mnt/pool/NAS/Media/8-Bit Legacy/podcast:/media/podcast" \\
    --env-file /mnt/pool/apps/8bit-pipeline/.env \\
    --user 950:950 \\
    --entrypoint python3 \\
    8bit-pipeline:latest \\
    /app/scripts/podcast/realign_transcript.py --batch

  echo
  echo "==> [3/4] pick_clips → render → preview (NO schedule)"
  # Inner script lives at /tmp/test-inner.sh, mounted into container as /tmp/runner.sh
  docker run --rm --name 8bit-test-pipeline \\
    -v /mnt/pool/apps/8bit-pipeline/data:/app/data \\
    -v /mnt/pool/apps/8bit-pipeline/config:/app/config \\
    -v "/mnt/pool/NAS/Media/8-Bit Legacy/podcast:/media/podcast" \\
    -v /tmp/test-inner.sh:/tmp/runner.sh:ro \\
    --env-file /mnt/pool/apps/8bit-pipeline/.env \\
    --user 950:950 \\
    --entrypoint bash \\
    8bit-pipeline:latest \\
    /tmp/runner.sh

  echo
  echo "==> [4/4] Results summary"
  ls -la "/mnt/pool/apps/8bit-pipeline/data/podcast/clips/${EPISODE_SAFE}/" | head -40
  echo
  echo "===== TEST DONE ====="
} > /tmp/test-on-episode-runner.out 2>&1
echo TEST_RUNNER_DONE >> /tmp/test-on-episode-runner.out
OUTER
chmod +x /tmp/test-outer.sh

# Ship both scripts to TrueNAS
scp -i "$SSH_KEY" -q /tmp/test-inner.sh /tmp/test-outer.sh "truenas_admin@${TRUENAS_IP}:/tmp/"

echo "==> Kicking off test via TrueNAS cronjob"
RESP=$(curl -s -X POST "http://${TRUENAS_IP}/api/v2.0/cronjob" \
  -H "Authorization: Bearer ${TRUENAS_API_KEY}" -H "Content-Type: application/json" \
  -d "{\"user\":\"root\",\"command\":\"bash /tmp/test-outer.sh\",\"description\":\"test ${EPISODE}\",\"schedule\":{\"minute\":\"0\",\"hour\":\"0\",\"dom\":\"1\",\"month\":\"1\",\"dow\":\"0\"},\"enabled\":false}")
JOB_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST "http://${TRUENAS_IP}/api/v2.0/cronjob/run" \
  -H "Authorization: Bearer ${TRUENAS_API_KEY}" -H "Content-Type: application/json" -d "{\"id\": $JOB_ID}" > /dev/null

echo "==> Polling test output (up to 60 min)"
LAST_LINE=""
for i in $(seq 1 720); do
  sleep 5
  LINE="$(ssh -i "$SSH_KEY" "truenas_admin@${TRUENAS_IP}" 'tail -1 /tmp/test-on-episode-runner.out 2>/dev/null' || true)"
  if [[ "$LINE" != "$LAST_LINE" && -n "$LINE" ]]; then
    echo "  [${i}×5s] $LINE"
    LAST_LINE="$LINE"
  fi
  if [[ "$LINE" == *TEST_RUNNER_DONE* ]]; then break; fi
done

echo
echo "==> Pulling output log + preview HTML + rendered MP4s back to Mac"
mkdir -p "/tmp/${EPISODE_SAFE}"
ssh -i "$SSH_KEY" "truenas_admin@${TRUENAS_IP}" 'cat /tmp/test-on-episode-runner.out' > "/tmp/${EPISODE_SAFE}/run.log"
rsync -az -e "ssh -i $SSH_KEY" \
  "truenas_admin@${TRUENAS_IP}:/mnt/pool/apps/8bit-pipeline/data/podcast/clips/${EPISODE_SAFE}/" \
  "/tmp/${EPISODE_SAFE}/" 2>&1 | tail -10

curl -s -X DELETE "http://${TRUENAS_IP}/api/v2.0/cronjob/id/${JOB_ID}" \
  -H "Authorization: Bearer ${TRUENAS_API_KEY}" > /dev/null

echo
echo "==> Done. Open the preview:"
echo "    open /tmp/${EPISODE_SAFE}/preview_queue.html"
echo
echo "==> Run log: /tmp/${EPISODE_SAFE}/run.log"
echo "==> Rendered MP4s: /tmp/${EPISODE_SAFE}/*.mp4"
echo "==> Rejected clips (if any): /tmp/${EPISODE_SAFE}/_rejected/"
