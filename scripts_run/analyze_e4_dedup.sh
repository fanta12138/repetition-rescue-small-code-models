#!/usr/bin/env bash
# E4 sensitivity: seeds are deterministic on locked tasks (v2_11 dup 10/10).
# Collapse identical instances (hash of structured-arm trajectory) and redo
# the preregistered McNemar tests on unique instances only.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816
python - <<'EOF'
import json, hashlib
from pathlib import Path
from eval.stat_test import mcnemar_exact

ROOTS = [Path("runs/E4v4"), Path("runs/E4v2lock"), Path("runs/E4v3lock")]
MODES = ["repair_structured", "repair_diverse", "repair_nudge_weak"]

rows, traj_hash = {}, {}
for m in MODES:
    rows[m] = {}
for root in ROOTS:
    for s in range(5):
        for m in MODES:
            for line in (root / f"seed{s}/{m}/metrics.jsonl").read_text().splitlines():
                r = json.loads(line)
                rows[m][(s, r["instance_id"])] = r
        for line in (root / f"seed{s}/repair_structured/trajectories.jsonl").read_text().splitlines():
            rec = json.loads(line)
            key = (s, rec.get("instance_id") or rec.get("task_id", "?"))
            traj_hash.setdefault(key, []).append(rec.get("extra", {}).get("response_excerpt", ""))

keys = sorted(set.intersection(*[set(rows[m]) for m in MODES]))
locked = [k for k in keys
          if (not rows["repair_structured"][k]["success"])
          and rows["repair_structured"][k]["repetition_events"] >= 2]

# collapse: group locked instances by (task, full structured trajectory hash)
groups = {}
for k in locked:
    h = hashlib.md5("\n".join(traj_hash.get(k, [])).encode()).hexdigest()
    groups.setdefault((k[1], h), []).append(k)

print(f"locked instances: {len(locked)} -> unique after collapse: {len(groups)}")
for (tid, h), members in sorted(groups.items()):
    print(f"  {tid} [{h[:8]}] x{len(members)}: seeds={[s for s, _ in members]}")

# dedup: keep one representative per group
unique = [members[0] for members in groups.values()]

def mcnemar(a, b, subset, label, alpha, min_disc=None):
    disc_ab = [k for k in subset if rows[a][k]["success"] and not rows[b][k]["success"]]
    disc_ba = [k for k in subset if rows[b][k]["success"] and not rows[a][k]["success"]]
    n = len(subset)
    ra = sum(rows[a][k]["success"] for k in subset) / n
    rb = sum(rows[b][k]["success"] for k in subset) / n
    p = mcnemar_exact(len(disc_ab), len(disc_ba))
    verdict = p < alpha and len(disc_ab) > len(disc_ba)
    if min_disc is not None:
        verdict = verdict and (len(disc_ab) + len(disc_ba)) >= min_disc
    print(f"[{label}] n={n}: {ra:.1%} vs {rb:.1%}, discordant "
          f"{len(disc_ab)}/{len(disc_ba)}, p={p:.5f} -> "
          f"{'PASS' if verdict else 'FAIL'}")

print("\n--- deduplicated rerun of preregistered tests ---")
mcnemar("repair_diverse", "repair_structured", unique, "P1 dedup", 0.025)
mcnemar("repair_nudge_weak", "repair_structured", unique, "P2 dedup", 0.025)
mcnemar("repair_diverse", "repair_nudge_weak", unique, "S1 dedup", 0.05)
EOF
