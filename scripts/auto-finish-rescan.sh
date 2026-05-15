#!/usr/bin/env bash
# Wait for the rescan PID, then run audit + dry-run apply automatically.
# Output: data/logs/auto-finish-<ts>.log
#
# Usage: ./scripts/auto-finish-rescan.sh <RESCAN_PID>
set -uo pipefail

PID="${1:?usage: auto-finish-rescan.sh <pid>}"
PROJECT="${HOME}/8bit-pricing"
LOG="${PROJECT}/data/logs/auto-finish-$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG") 2>&1
echo "=== auto-finish-rescan PID=$PID started $(date) ==="
echo "Waiting for rescan PID $PID to exit..."

# Poll loop — `wait` only works for child processes
while kill -0 "$PID" 2>/dev/null; do
  sleep 60
done

echo "=== Rescan PID $PID exited at $(date) ==="

# Find the freshest search-refresh CSV produced today
CSV=$(ls -t "${PROJECT}/data/logs/"search-refresh-2026*.csv 2>/dev/null | head -1)
if [[ -z "$CSV" ]]; then
  echo "FATAL: no search-refresh CSV found"
  exit 2
fi
echo "Using CSV: $CSV ($(wc -l < "$CSV") lines, $(stat -c%s "$CSV" 2>/dev/null || stat -f%z "$CSV") bytes)"

# Run audit
echo ""
echo "=== AUDIT ==="
cd "$PROJECT" && python3 scripts/audit-cross-console-pricing.py "$CSV" 2>&1 || echo "audit failed (non-fatal)"

# Run applier in dry-run mode against the fresh CSV.
# --skip-breaker-check is NOT used — if breaker is tripped, the dry-run will print
# the FATAL and exit, which is fine (the user must reset the breaker explicitly).
echo ""
echo "=== APPLIER DRY-RUN ==="
python3 scripts/apply-truth-set.py --csv "$CSV" --max-age-hours 999 --skip-breaker-check

echo ""
echo "=== DONE $(date) ==="
echo "Review queue CSVs in ${PROJECT}/data/logs/review-queue-*.csv"
echo "To actually apply: python3 scripts/apply-truth-set.py --csv $CSV --apply --skip-breaker-check"
