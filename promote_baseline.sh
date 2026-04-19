#!/bin/bash
# Promote a scored eval run to the committed baseline.
#
# Usage:
#   ./eval/promote_baseline.sh eval/results/local_20260419_scored.json
#   ./eval/promote_baseline.sh  # picks the most recent *_scored.json

set -e
EVAL_DIR="$(cd "$(dirname "$0")" && pwd)"
BASELINE="$EVAL_DIR/baseline_scored.json"

if [ -n "$1" ]; then
    SRC="$1"
else
    SRC="$(ls -t "$EVAL_DIR"/results/*_scored.json 2>/dev/null | head -1)"
    if [ -z "$SRC" ]; then
        echo "No scored results found in eval/results/"
        exit 1
    fi
fi

if [ ! -f "$SRC" ]; then
    echo "File not found: $SRC"
    exit 1
fi

# Show summary before promoting
PASS_RATE=$(python3 -c "import json; d=json.load(open('$SRC')); print(d['summary']['pass_rate'])")
AVG_SCORE=$(python3 -c "import json; d=json.load(open('$SRC')); print(d['summary']['average_score'])")
TOTAL=$(python3 -c "import json; d=json.load(open('$SRC')); print(d['summary']['total_prompts'])")

echo "Promoting: $(basename "$SRC")"
echo "  Prompts: $TOTAL"
echo "  Pass rate: ${PASS_RATE}%"
echo "  Avg score: $AVG_SCORE"

# Compare with existing baseline if present
if [ -f "$BASELINE" ]; then
    echo ""
    echo "--- Comparison with current baseline ---"
    python3 "$EVAL_DIR/compare.py" "$BASELINE" "$SRC"
    echo ""
    read -p "Replace baseline? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

cp "$SRC" "$BASELINE"
echo "Baseline updated: $BASELINE"
echo "Run 'git add eval/baseline_scored.json && git commit' to commit it."
