#!/usr/bin/env bash
# E3 smoke: trigger verification + first-attempt fairness.
# v2: limit 11 covers lock-in task v2_11; v3: limit 7 covers v3_07.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816

python -m scripts.run_e0 --config configs/e3_lockbreak.yaml --dataset v2 \
    --modes repair_structured,repair_diverse,repair_tempbump \
    --seeds 0 --limit 11 --out runs/E3_smoke_v2
python -m scripts.run_e0 --config configs/e3_lockbreak.yaml --dataset v3 \
    --modes repair_structured,repair_diverse,repair_tempbump \
    --seeds 0 --limit 7 --out runs/E3_smoke_v3

echo "--- E3 lock metrics (v2 v2_11 / v3 v3_07) ---"
python - <<'EOF'
import json
from pathlib import Path

for root, tid in [("runs/E3_smoke_v2", "v2_11"), ("runs/E3_smoke_v3", "v3_07")]:
    for mode in ["repair_structured", "repair_diverse", "repair_tempbump"]:
        row = next(json.loads(l) for l in
                   Path(f"{root}/seed0/{mode}/metrics.jsonl").read_text().splitlines()
                   if json.loads(l)["instance_id"] == tid)
        print(f"{root} {mode} {tid}: success={row['success']} iters={row['llm_calls']} "
              f"rep={row['repetition_events']} interv={row['interventions']} "
              f"tokens={row['total_tokens']}")

print("--- first-attempt fairness: iters=1 tasks must have identical tokens ---")
for root in ["runs/E3_smoke_v2", "runs/E3_smoke_v3"]:
    a = {r["instance_id"]: r for r in map(json.loads,
         Path(f"{root}/seed0/repair_structured/metrics.jsonl").read_text().splitlines())}
    for mode in ["repair_diverse", "repair_tempbump"]:
        b = {r["instance_id"]: r for r in map(json.loads,
             Path(f"{root}/seed0/{mode}/metrics.jsonl").read_text().splitlines())}
        for tid, ra in a.items():
            rb = b[tid]
            if ra["llm_calls"] == 1 and rb["llm_calls"] == 1 and ra["total_tokens"] != rb["total_tokens"]:
                print(f"MISMATCH {root} {mode} {tid}: {ra['total_tokens']} vs {rb['total_tokens']}")
    print(f"{root}: fairness check done")
EOF
