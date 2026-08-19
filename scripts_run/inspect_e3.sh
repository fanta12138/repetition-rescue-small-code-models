#!/usr/bin/env bash
# E3 checks: seed sanity + what repair_diverse actually did on v2_11/v3_07.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816
python - <<'EOF'
import json, hashlib
from pathlib import Path

print("--- seed sanity (completion-hash pairwise, E3v2+E3v3) ---")
for root, modes in [("runs/E3v2", None), ("runs/E3v3", None)]:
    base = Path(root)
    for mode in ["repair_diverse", "repair_tempbump"]:
        hashes = {}
        for s in range(5):
            texts = [json.loads(l).get("extra", {}).get("response_excerpt", "")
                     for l in (base / f"seed{s}/{mode}/trajectories.jsonl")
                     .read_text(encoding="utf-8").splitlines()]
            hashes[s] = hashlib.md5("\n".join(texts).encode()).hexdigest()
        dups = [(a, b) for a in range(5) for b in range(a + 1, 5) if hashes[a] == hashes[b]]
        print(f"{root}/{mode}: duplicate hash pairs {dups or 'none'}")

print("\n--- v2_11 under repair_diverse seed0: what changed after the nudge? ---")
traj = Path("runs/E3v2/seed0/repair_diverse/trajectories.jsonl")
steps = [json.loads(l) for l in traj.read_text(encoding="utf-8").splitlines()
         if json.loads(l)["instance_id"] == "v2_11"]
for t in steps:
    if t.get("role") != "coder":
        continue
    ex = t.get("extra", {}).get("response_excerpt", "")
    print(f"[step {t.get('step')}] tokens={t.get('completion_tokens')} head: {ex[:160]!r}")
EOF
