#!/usr/bin/env bash
# Autonomous end-to-end pricing-reset finisher.
#
# Waits for a rescan PID to exit, runs the audit, runs the apply in dry-run
# to get classification counts, then automatically runs the REAL apply if
# the sanity gates pass. If any gate fails, stops and logs why.
#
# Output: data/logs/auto-finish-<ts>.log
#
# Usage: ./scripts/auto-finish-rescan.sh <RESCAN_PID>
set -uo pipefail

PID="${1:?usage: auto-finish-rescan.sh <pid>}"
PROJECT="${HOME}/8bit-pricing"
TS=$(date +%Y%m%d_%H%M%S)
LOG="${PROJECT}/data/logs/auto-finish-${TS}.log"

exec > >(tee -a "$LOG") 2>&1
echo "=== auto-finish-rescan PID=$PID started $(date) ==="
echo "Waiting for rescan PID $PID to exit..."

while kill -0 "$PID" 2>/dev/null; do
  sleep 60
done

echo ""
echo "=== Rescan PID $PID exited at $(date) ==="

CSV=$(ls -t "${PROJECT}/data/logs/"search-refresh-2026*.csv 2>/dev/null | head -1)
if [[ -z "$CSV" ]]; then
  echo "FATAL: no search-refresh CSV found"
  exit 2
fi
CSV_BYTES=$(stat -c%s "$CSV" 2>/dev/null || stat -f%z "$CSV")
CSV_LINES=$(wc -l < "$CSV")
echo "CSV: $CSV ($CSV_LINES lines, $CSV_BYTES bytes)"

# Sanity gate 0: CSV must be substantial
if [[ "$CSV_LINES" -lt 3000 ]]; then
  echo "GATE FAIL: CSV has only $CSV_LINES lines — rescan likely failed early. Aborting."
  exit 3
fi

# Audit (non-fatal — log only)
echo ""
echo "=== AUDIT ==="
cd "$PROJECT"
python3 scripts/audit-cross-console-pricing.py "$CSV" 2>&1 | tail -50 || echo "(audit warned)"

# Dry-run to capture classification counts
echo ""
echo "=== APPLIER DRY-RUN ==="
DRYRUN_OUT="${PROJECT}/data/logs/dryrun-summary-${TS}.txt"
python3 scripts/apply-truth-set.py --csv "$CSV" --max-age-hours 999 --skip-breaker-check 2>&1 | tee "$DRYRUN_OUT"

# Parse counts from dry-run output
APPLY_COUNT=$(grep -E "^\[[^]]+\]   APPLY " "$DRYRUN_OUT" | awk '{print $NF}' | tr -d '\r')
QERR_COUNT=$(grep -E "^\[[^]]+\]   QUARANTINE_ERR " "$DRYRUN_OUT" | awk '{print $NF}' | tr -d '\r')
QDOWN_COUNT=$(grep -E "^\[[^]]+\]   QUARANTINE_DOWN " "$DRYRUN_OUT" | awk '{print $NF}' | tr -d '\r')
TITLE_COUNT=$(grep -E "^\[[^]]+\]   SKIP_TITLE " "$DRYRUN_OUT" | awk '{print $NF}' | tr -d '\r')
INVALID_COUNT=$(grep -E "^\[[^]]+\]   INVALID " "$DRYRUN_OUT" | awk '{print $NF}' | tr -d '\r')

echo ""
echo "=== CLASSIFICATION ==="
echo "APPLY            : $APPLY_COUNT"
echo "QUARANTINE_ERR   : $QERR_COUNT"
echo "QUARANTINE_DOWN  : $QDOWN_COUNT"
echo "SKIP_TITLE       : $TITLE_COUNT"
echo "INVALID(NO_MATCH): $INVALID_COUNT"

# Default missing values to 0
APPLY_COUNT=${APPLY_COUNT:-0}
QERR_COUNT=${QERR_COUNT:-0}
QDOWN_COUNT=${QDOWN_COUNT:-0}
TITLE_COUNT=${TITLE_COUNT:-0}
INVALID_COUNT=${INVALID_COUNT:-0}

# Sanity gates before real apply
GATES_PASS=1
GATE_REASONS=""

# Gate 1: APPLY count must be sensible (100 ≤ N ≤ 4000)
#   <100  = matcher broken or nothing to fix; either way needs human eyes
#   >4000 = >50% of catalog would change — mass-corruption suspect
if [[ "$APPLY_COUNT" -lt 100 ]]; then
  GATES_PASS=0
  GATE_REASONS="${GATE_REASONS}APPLY too low ($APPLY_COUNT < 100); "
fi
if [[ "$APPLY_COUNT" -gt 4000 ]]; then
  GATES_PASS=0
  GATE_REASONS="${GATE_REASONS}APPLY too high ($APPLY_COUNT > 4000 — mass corruption suspect); "
fi
# Gate 2: QUARANTINE_ERR (matcher-error suspects) under 800
#   Past full runs had ~127. Much higher = matcher regression.
if [[ "$QERR_COUNT" -gt 800 ]]; then
  GATES_PASS=0
  GATE_REASONS="${GATE_REASONS}QUARANTINE_ERR too high ($QERR_COUNT > 800); "
fi
# Gate 3: SKIP_TITLE small — we fixed the 26 known corruptions yesterday
if [[ "$TITLE_COUNT" -gt 100 ]]; then
  GATES_PASS=0
  GATE_REASONS="${GATE_REASONS}SKIP_TITLE too high ($TITLE_COUNT > 100 — new title corruption?); "
fi

echo ""
if [[ "$GATES_PASS" -ne 1 ]]; then
  echo "=== GATES FAILED ==="
  echo "Reasons: $GATE_REASONS"
  echo "Not applying. Review queue CSVs in ${PROJECT}/data/logs/review-queue-*.csv"
  echo "To manually apply: python3 scripts/apply-truth-set.py --csv $CSV --apply --skip-breaker-check"
  exit 4
fi

echo "=== GATES PASSED — proceeding with REAL APPLY ==="
echo "Will write $APPLY_COUNT price changes to Shopify."

# Real apply
APPLY_OUT="${PROJECT}/data/logs/applied-${TS}.log"
echo ""
echo "=== REAL APPLY $(date) ==="
python3 scripts/apply-truth-set.py --csv "$CSV" --apply --max-age-hours 999 --skip-breaker-check 2>&1 | tee "$APPLY_OUT"
APPLY_EXIT=$?

echo ""
echo "=== APPLY EXIT: $APPLY_EXIT ==="
echo "=== DONE $(date) ==="
echo ""
echo "Summary:"
echo "  Rescan CSV: $CSV ($CSV_LINES lines)"
echo "  Apply log:  $APPLY_OUT"
echo "  Review queues: ${PROJECT}/data/logs/review-queue-*-${TS}.csv"
echo ""
echo "Quarantine totals for human review:"
echo "  QUARANTINE_ERR  (matcher-error suspects): $QERR_COUNT"
echo "  QUARANTINE_DOWN (>30% price drops):       $QDOWN_COUNT"
echo "  SKIP_TITLE      (corrupted titles):       $TITLE_COUNT"
echo "  INVALID         (no PriceCharting match): $INVALID_COUNT"

exit $APPLY_EXIT
