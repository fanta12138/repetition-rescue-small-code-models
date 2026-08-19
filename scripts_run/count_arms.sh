#!/usr/bin/env bash
# Count metrics rows per seed/arm for candidate 7B source runs.
set -uo pipefail
cd /mnt/g/paper0816/runs
for run in E3v2 E4v2lock E4v4 E5; do
  echo "== $run"
  for d in $run/seed*; do
    for a in "$d"/*/; do
      arm=$(basename "$a")
      n=$(wc -l < "$a/metrics.jsonl" 2>/dev/null || echo 0)
      echo "  $(basename $d)/$arm = $n"
    done
  done
done
