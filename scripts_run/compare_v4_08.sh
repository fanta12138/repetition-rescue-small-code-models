#!/usr/bin/env bash
# Compare per-step token/wall fingerprints of 7B vs 3B v4_08 rescue runs.
set -uo pipefail
cd /mnt/g/paper0816
python3 - <<'EOF'
import json
import hashlib


def steps(run, seed):
    out = []
    p = f"runs/{run}/seed{seed}/repair_diverse/trajectories.jsonl"
    for line in open(p):
        t = json.loads(line)
        if t["instance_id"] == "v4_08" and t.get("role") == "coder":
            ex = (t.get("extra") or {}).get("response_excerpt", "")
            out.append((t["step"], t["prompt_tokens"], t["completion_tokens"],
                        round(t["wall_time"], 2),
                        hashlib.md5(ex.encode()).hexdigest()[:8]))
    return out


for run, seed in [("E4v4", 0), ("E6lock", 2)]:
    print(run, "coder steps:", steps(run, seed))
# structured arm should differ between models (sanity check)
for run, seed in [("E4v4", 0), ("E6lock", 2)]:
    out = []
    p = f"runs/{run}/seed{seed}/repair_structured/trajectories.jsonl"
    for line in open(p):
        t = json.loads(line)
        if t["instance_id"] == "v4_08" and t.get("role") == "coder":
            out.append((t["step"], t["completion_tokens"], round(t["wall_time"], 2)))
    print(run, "structured:", out)
EOF
