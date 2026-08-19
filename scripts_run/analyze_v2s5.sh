#!/usr/bin/env bash
# Aggregate 5-seed E0v2s5 results + McNemar tests.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816
echo "===== metrics ====="
python -m eval.metrics --run runs/E0v2s5
echo
echo "===== McNemar ====="
python -m eval.stat_test --run runs/E0v2s5
echo
echo "===== task matrix ====="
python -m scripts.task_matrix runs/E0v2s5
