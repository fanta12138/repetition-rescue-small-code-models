#!/usr/bin/env bash
# E2 analysis: metrics + preregistered McNemar comparisons + task matrix.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816
echo "===== metrics ====="
python -m eval.metrics --run runs/E2
echo
echo "===== McNemar (preregistered pairs) ====="
python -m eval.stat_test --run runs/E2 \
    --pairs repair:no_feedback repair_structured:no_feedback repair:direct
echo
echo "===== task matrix ====="
python -m scripts.task_matrix runs/E2
