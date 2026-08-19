#!/usr/bin/env bash
# Check whether seed3 and seed4 runs are identical (would indicate seed not honored).
set -euo pipefail
cd /mnt/g/paper0816/runs/E0v2s5
for m in direct repair random_reflection no_feedback; do
    if diff -q "seed3/$m/metrics.jsonl" "seed4/$m/metrics.jsonl" >/dev/null; then
        echo "$m: metrics IDENTICAL"
    else
        echo "$m: metrics differ"
    fi
done
ls seed3/direct/ | head
for f in $(ls seed3/direct/); do
    if [ -f "seed4/direct/$f" ]; then
        if diff -q "seed3/direct/$f" "seed4/direct/$f" >/dev/null; then
            echo "direct/$f: IDENTICAL"
        else
            echo "direct/$f: differ"
        fi
    fi
done
