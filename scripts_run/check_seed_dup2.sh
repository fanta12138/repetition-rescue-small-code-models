#!/usr/bin/env bash
# Compare success vectors and completion texts between seed3 and seed4.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816
python - <<'EOF'
import json, hashlib
from pathlib import Path

base = Path("runs/E0v2s5")
for mode in ["direct", "repair", "random_reflection", "no_feedback"]:
    same_succ = same_text = total = 0
    for row3, row4 in zip(
        map(json.loads, (base / f"seed3/{mode}/metrics.jsonl").read_text().splitlines()),
        map(json.loads, (base / f"seed4/{mode}/metrics.jsonl").read_text().splitlines()),
    ):
        total += 1
        same_succ += row3["success"] == row4["success"]
        same_text += row3["total_tokens"] == row4["total_tokens"]
    # hash model completions from trajectories (one line per step)
    def traj_hash(seed):
        p = base / f"seed{seed}/{mode}/trajectories.jsonl"
        texts = []
        for line in p.read_text(encoding="utf-8").splitlines():
            t = json.loads(line)
            texts.append(t.get("extra", {}).get("response_excerpt", ""))
        return hashlib.md5("\n".join(texts).encode()).hexdigest()
    h3, h4 = traj_hash(3), traj_hash(4)
    print(f"{mode}: success identical {same_succ}/{total}, "
          f"token-count identical {same_text}/{total}, "
          f"completion-text {'IDENTICAL' if h3 == h4 else 'differ'}")
EOF
