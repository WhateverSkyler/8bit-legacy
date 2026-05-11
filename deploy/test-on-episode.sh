#!/usr/bin/env bash
# Run the shorts pipeline on a specific episode WITHOUT publishing.
#
# Spins up a one-shot docker container with the 8bit-pipeline image but
# overrides the entrypoint so drop_watcher does NOT start. Runs:
#   1. realign_transcript.py — fixes whisperX-missing transcripts (caption sync)
#   2. pick_clips → render → preview HTML generation
#
# After completion, pulls the preview HTML + all rendered MP4s back to /tmp
# on the Mac so the user can review locally before approving anything to ship.
#
# Usage:
#   ./deploy/test-on-episode.sh "Episode May 5 2026"
#   ./deploy/test-on-episode.sh "Episode May 5 2026" /path/to/source/full.mp4
#
# After preview, to ship the approved clips:
#   ./deploy/schedule-from-preview.sh "Episode May 5 2026" 2026-05-12

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

EPISODE="${1:?usage: $0 \"Episode May 5 2026\" \"<full-video-stem>\"}"
EPISODE_SAFE="$(echo "$EPISODE" | tr ' ' '_')"
# The transcript stem (without _1080p.json suffix). Default matches May 5.
# This is the FULL EPISODE transcript — we pick from it via chunked 30-min
# windows so all good content (including content NOT in any auto-segmented
# topic video) gets considered.
FULL_TRANSCRIPT_STEM="${2:-8-Bit Podcast May 5 2026 FULL FINAL V2}"

TRUENAS_IP="${TRUENAS_IP:-192.168.4.2}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
TRUENAS_API_KEY="${TRUENAS_API_KEY:-$(grep ^TRUENAS_API_KEY "$REPO_ROOT/config/.env" 2>/dev/null | cut -d= -f2 | tr -d '"' || echo '')}"

if [[ -z "$TRUENAS_API_KEY" ]]; then
  echo "FATAL: set TRUENAS_API_KEY (or put it in config/.env)" >&2
  exit 1
fi

echo "==> Building test runner script"
cat > /tmp/test-on-episode-runner.sh <<RUNNER
#!/bin/bash
set -e
{
  echo "===== EPISODE: $EPISODE ====="
  echo "===== \$(date) ====="
  echo

  echo "==> [1/4] Stop any running 8bit-pipeline (so we own /app/data exclusively)"
  docker stop 8bit-pipeline 2>/dev/null || true
  sleep 2

  echo "==> [2/4] Re-align May 5 transcripts via whisperX (refines word timing to ±50ms)"
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
  echo "==> [3/4] Pipeline: pick_clips (chunked, FROM FULL ONLY) → render → preview (NO schedule)"
  # We pick from the FULL EPISODE transcript ONLY (not the auto-segmented topic
  # videos), in 30-minute chunked windows. This catches good content that
  # didn't make it into any auto-segmented topic. We do each stage explicitly
  # so the schedule stage (which would publish) never runs.
  docker run --rm --name 8bit-test-pipeline \\
    -v /mnt/pool/apps/8bit-pipeline/data:/app/data \\
    -v /mnt/pool/apps/8bit-pipeline/config:/app/config \\
    -v "/mnt/pool/NAS/Media/8-Bit Legacy/podcast:/media/podcast" \\
    --env-file /mnt/pool/apps/8bit-pipeline/.env \\
    --user 950:950 \\
    --entrypoint bash \\
    8bit-pipeline:latest \\
    -c "
      set -e
      cd /app
      FULL_TRANSCRIPT='/app/data/podcast/transcripts/${FULL_TRANSCRIPT_STEM}_1080p.json'
      if [ ! -f \"\$FULL_TRANSCRIPT\" ]; then
        echo \"FATAL: full transcript not found: \$FULL_TRANSCRIPT\"
        ls /app/data/podcast/transcripts/
        exit 1
      fi
      echo '--- clearing old clips_plan/_all.json so we only get FULL picks ---'
      rm -f /app/data/podcast/clips_plan/*.json
      echo '--- pick_clips: FROM FULL EPISODE ONLY, chunked 30-min windows ---'
      python3 scripts/podcast/pick_clips.py \"\$FULL_TRANSCRIPT\" --chunk-minutes 30 --target-count 30
      echo '--- copying picks to _all.json so render_clip.py finds them ---'
      cp /app/data/podcast/clips_plan/${FULL_TRANSCRIPT_STEM}_1080p.json /app/data/podcast/clips_plan/_all.json
      echo '--- render_clips ---'
      python3 scripts/podcast/render_clip.py --batch /app/data/podcast/clips_plan/_all.json --episode \"$EPISODE\"
      echo '--- preview_queue ---'
      START_DATE=\$(date -d '+1 day' +%Y-%m-%d 2>/dev/null || date -v+1d +%Y-%m-%d)
      python3 scripts/podcast/preview_queue.py --episode \"$EPISODE\" --start-date \$START_DATE
    "

  echo
  echo "==> [4/4] Results summary"
  ls -la "/mnt/pool/apps/8bit-pipeline/data/podcast/clips/${EPISODE_SAFE}/" | head -40
  echo
  echo "===== TEST DONE ====="
} > /tmp/test-on-episode-runner.out 2>&1
echo TEST_RUNNER_DONE >> /tmp/test-on-episode-runner.out
RUNNER
chmod +x /tmp/test-on-episode-runner.sh

scp -i "$SSH_KEY" -q /tmp/test-on-episode-runner.sh "truenas_admin@${TRUENAS_IP}:/tmp/"

echo "==> Kicking off test via TrueNAS cronjob (rebuild + realign + render + preview)"
RESP=$(curl -s -X POST "http://${TRUENAS_IP}/api/v2.0/cronjob" \
  -H "Authorization: Bearer ${TRUENAS_API_KEY}" -H "Content-Type: application/json" \
  -d "{\"user\":\"root\",\"command\":\"bash /tmp/test-on-episode-runner.sh\",\"description\":\"test ${EPISODE}\",\"schedule\":{\"minute\":\"0\",\"hour\":\"0\",\"dom\":\"1\",\"month\":\"1\",\"dow\":\"0\"},\"enabled\":false}")
JOB_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST "http://${TRUENAS_IP}/api/v2.0/cronjob/run" \
  -H "Authorization: Bearer ${TRUENAS_API_KEY}" -H "Content-Type: application/json" -d "{\"id\": $JOB_ID}" > /dev/null

echo "==> Polling test output (up to 60 min — realign is ~5 min/transcript, render is ~30s/clip)"
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
