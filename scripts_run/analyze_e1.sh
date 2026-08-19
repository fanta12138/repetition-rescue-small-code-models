#!/usr/bin/env bash
# E1 analysis: metrics + preregistered McNemar comparisons + task matrix.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816
echo "===== metrics ====="
python -m eval.metrics --run runs/E1
echo
echo "===== McNemar (preregistered pairs) ====="
python -m eval.stat_test --run runs/E1 \
    --pairs repair_structured:no_feedback repair_contrast:no_feedback \
            repair_structured:repair repair_contrast:repair
echo
echo "===== task matrix ====="
python -m scripts.task_matrix runs/E1
