#!/usr/bin/env bash
# E2 seed sanity: pairwise compare completion-text hashes across seeds 0-4.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816
python - <<'EOF'
import json, hashlib
from pathlib import Path

base = Path("runs/E2")
seeds = [0, 1, 2, 3, 4]
for mode in ["direct", "repair", "repair_structured", "no_feedback"]:
    hashes = {}
    succ = {}
    for s in seeds:
        texts = []
        for line in (base / f"seed{s}/{mode}/trajectories.jsonl").read_text(encoding="utf-8").splitlines():
            texts.append(json.loads(line).get("extra", {}).get("response_excerpt", ""))
        hashes[s] = hashlib.md5("\n".join(texts).encode()).hexdigest()
        succ[s] = [r["success"] for r in
                   map(json.loads, (base / f"seed{s}/{mode}/metrics.jsonl").read_text().splitlines())]
    dup_pairs = [(a, b) for i, a in enumerate(seeds) for b in seeds[i+1:] if hashes[a] == hashes[b]]
    same_succ = sum(1 for i, a in enumerate(seeds) for b in seeds[i+1:] if succ[a] == succ[b])
    n_pairs = len(seeds) * (len(seeds) - 1) // 2
    print(f"{mode}: completion-hash duplicate pairs {len(dup_pairs)}/{n_pairs}"
          f"{dup_pairs if dup_pairs else ''}, success-vector identical {same_succ}/{n_pairs}")
EOF
