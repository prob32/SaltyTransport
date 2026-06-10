#!/usr/bin/env bash
# SaltyTransport validation harness.
#
# Runs vic3-tiger against the mod. Requires:
#   - vic3-tiger binary (override with $VIC3_TIGER)
#   - Vanilla game files (set $VIC3_GAME_DIR to the folder that contains game/
#     or the game/ folder itself, e.g. /opt/vic3)
#
# Usage:
#   tools/validate.sh                  # full report (human readable)
#   tools/validate.sh --json           # machine readable, written to tiger-report.json
#   tools/validate.sh --baseline       # snapshot current report as the suppression baseline
#   tools/validate.sh --new            # only NEW issues since the baseline
#
# The baseline lives at tools/tiger-baseline.json (committed) so reviews only
# surface regressions, not pre-existing noise.

set -euo pipefail

MOD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIGER="${VIC3_TIGER:-/opt/tools/vic3-tiger-linux-v1.19.0/vic3-tiger}"
GAME_DIR="${VIC3_GAME_DIR:-/opt/vic3}"
BASELINE="$MOD_DIR/tools/tiger-baseline.json"
CONF="$MOD_DIR/vic3-tiger.conf"

if [[ ! -x "$TIGER" ]]; then
    echo "ERROR: vic3-tiger not found at $TIGER (set \$VIC3_TIGER)" >&2
    exit 2
fi
if [[ ! -d "$GAME_DIR" ]]; then
    echo "ERROR: game dir not found at $GAME_DIR (set \$VIC3_GAME_DIR)" >&2
    echo "Tiger needs a copy of the Victoria 3 game files to resolve references." >&2
    exit 2
fi

ARGS=(--game "$GAME_DIR" --config "$CONF")

case "${1:-}" in
    --json)
        "$TIGER" "${ARGS[@]}" --json "$MOD_DIR" > "$MOD_DIR/tiger-report.json"
        echo "Wrote tiger-report.json ($(grep -c '"key"' "$MOD_DIR/tiger-report.json" || true) findings)"
        ;;
    --baseline)
        "$TIGER" "${ARGS[@]}" --json "$MOD_DIR" > "$BASELINE"
        echo "Baseline updated: $BASELINE"
        ;;
    --new)
        if [[ ! -f "$BASELINE" ]]; then
            echo "No baseline yet; run tools/validate.sh --baseline first" >&2
            exit 2
        fi
        "$TIGER" "${ARGS[@]}" --suppress "$BASELINE" "$MOD_DIR"
        ;;
    *)
        "$TIGER" "${ARGS[@]}" "$MOD_DIR"
        ;;
esac
