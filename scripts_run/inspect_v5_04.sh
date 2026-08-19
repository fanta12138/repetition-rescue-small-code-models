#!/usr/bin/env bash
# Inspect v5_04 per-step code hashes: is it verbatim repetition or a 2-cycle?
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816

python - <<'EOF'
import json, hashlib
for seed in [0, 1]:
    print(f"=== seed {seed} v5_04 ===")
    for line in open(f"runs/E5_screen/seed{seed}/repair_structured/trajectories.jsonl"):
        t = json.loads(line)
        if t["instance_id"] != "v5_04" or t["role"] != "coder":
            continue
        ex = t["extra"]["response_excerpt"]
        h = hashlib.md5(ex.encode()).hexdigest()[:8]
        print(f"step {t['step']}: hash={h} len={len(ex)}")
EOF
