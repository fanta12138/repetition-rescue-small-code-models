#!/usr/bin/env bash
# Smoke test for E1 new arms: 2 tasks x seed 0.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816
python -m scripts.run_e0 --config configs/e1_actionable.yaml --dataset v2 \
    --seeds 0 --limit 2 --out runs/E1_dryrun
echo "--- dryrun metrics ---"
cat runs/E1_dryrun/seed0/repair_structured/metrics.jsonl
cat runs/E1_dryrun/seed0/repair_contrast/metrics.jsonl
echo "--- sample feedback from trajectory (structured, iter2) ---"
grep -o '"response_excerpt"' runs/E1_dryrun/seed0/repair_structured/trajectories.jsonl | head -1 || true
