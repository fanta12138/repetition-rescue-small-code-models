#!/usr/bin/env bash
# E4 analysis per analysis/e4_preregistration.md (frozen before the run):
# seed validity, locked-subset definition, P1/P2/S1 McNemar tests,
# regression guard, fairness spot-check, per-task recovery, token cost.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816

echo "===== 0. seed validity: completion-hash duplicate pairs ====="
python - <<'EOF'
import json, hashlib
from pathlib import Path

ROOTS = [Path("runs/E4v4"), Path("runs/E4v2lock"), Path("runs/E4v3lock")]
MODES = ["repair_structured", "repair_diverse", "repair_nudge_weak"]
seeds = [0, 1, 2, 3, 4]
for root in ROOTS:
    for mode in MODES:
        hashes = {}
        for s in seeds:
            texts = [json.loads(l).get("extra", {}).get("response_excerpt", "")
                     for l in (root / f"seed{s}/{mode}/trajectories.jsonl")
                     .read_text(encoding="utf-8").splitlines()]
            hashes[s] = hashlib.md5("\n".join(texts).encode()).hexdigest()
        dup = [(a, b) for i, a in enumerate(seeds) for b in seeds[i+1:]
               if hashes[a] == hashes[b]]
        print(f"{root.name}/{mode}: dup pairs {len(dup)}/10 {dup or ''}")
EOF

echo
echo "===== 1. pooled locked-subset analysis (preregistered) ====="
python - <<'EOF'
import json
from pathlib import Path
from eval.stat_test import mcnemar_exact

ROOTS = [Path("runs/E4v4"), Path("runs/E4v2lock"), Path("runs/E4v3lock")]
MODES = ["repair_structured", "repair_diverse", "repair_nudge_weak"]

# rows[mode][(seed, task)] = metrics row
rows = {m: {} for m in MODES}
for root in ROOTS:
    for s in range(5):
        for m in MODES:
            for line in (root / f"seed{s}/{m}/metrics.jsonl").read_text().splitlines():
                r = json.loads(line)
                rows[m][(s, r["instance_id"])] = r

keys = sorted(set(rows["repair_structured"]) & set(rows["repair_diverse"])
              & set(rows["repair_nudge_weak"]))
print(f"paired instances per arm: {len(keys)}")

# preregistered locked-instance definition: structured failed AND rep >= 2
locked = [k for k in keys
          if (not rows["repair_structured"][k]["success"])
          and rows["repair_structured"][k]["repetition_events"] >= 2]
print(f"locked instances: {len(locked)} -> {sorted(locked)}")

def mcnemar(a, b, subset, label, alpha, min_disc=None):
    pa = {k: rows[a][k]["success"] for k in subset}
    pb = {k: rows[b][k]["success"] for k in subset}
    disc_ab = [k for k in subset if pa[k] and not pb[k]]
    disc_ba = [k for k in subset if pb[k] and not pa[k]]
    n = len(subset)
    ra = sum(pa.values()) / n if n else 0
    rb = sum(pb.values()) / n if n else 0
    p = mcnemar_exact(len(disc_ab), len(disc_ba))
    verdict = p < alpha and len(disc_ab) > len(disc_ba)
    if min_disc is not None:
        verdict = verdict and (len(disc_ab) + len(disc_ba)) >= min_disc
    print(f"[{label}] {a} vs {b} on n={n}: {ra:.1%} vs {rb:.1%}, "
          f"discordant {len(disc_ab)}/{len(disc_ba)}, p={p:.5f} "
          f"-> {'PASS' if verdict else 'FAIL'} (alpha={alpha})")
    if disc_ab:
        print(f"    gained by {a}: {sorted(k[1] for k in disc_ab)}")
    if disc_ba:
        print(f"    lost to {b}: {sorted(k[1] for k in disc_ba)}")
    return verdict

p1 = mcnemar("repair_diverse", "repair_structured", locked,
             "P1 effect exists", 0.025, min_disc=6)
p2 = mcnemar("repair_nudge_weak", "repair_structured", locked,
             "P2 alt-explanation (weak vs structured)", 0.025)
s1 = mcnemar("repair_diverse", "repair_nudge_weak", locked,
             "S1 specificity (diverse vs weak)", 0.05)

print("\ninterpretation tree:")
if p1 and not p2 and s1:
    print("  STRONG: switch-approach instruction is the active ingredient.")
elif p1 and p2 and not s1:
    print("  DOWNGRADED: effect real but attributable to repetition-aware retry.")
elif p1:
    print("  MIXED: P1 passed; check P2/S1 details above.")
else:
    print("  NULL: E3's 5/0 was small-sample noise; lock intervention ineffective.")

# regression guard on NON-locked instances (preregistered: losses <= 1)
nonlocked = [k for k in keys if k not in set(locked)]
print(f"\n===== 2. regression guard (non-locked, n={len(nonlocked)}) =====")
for arm in ["repair_diverse", "repair_nudge_weak"]:
    losses = [k for k in nonlocked
              if rows["repair_structured"][k]["success"] and not rows[arm][k]["success"]]
    print(f"{arm}: losses = {len(losses)} {sorted(k[1] for k in losses) or ''}"
          f" -> {'OK' if len(losses) <= 1 else 'GUARD TRIPPED'}")

# fairness spot-check: zero-repetition instances must be token-identical
print("\n===== 3. fairness spot-check (rep=0 instances) =====")
mismatch = 0
for k in keys:
    s = rows["repair_structured"][k]
    if s["repetition_events"] == 0:
        for arm in ["repair_diverse", "repair_nudge_weak"]:
            if rows[arm][k]["total_tokens"] != s["total_tokens"]:
                print(f"MISMATCH {k} {arm}: {rows[arm][k]['total_tokens']} vs {s['total_tokens']}")
                mismatch += 1
print(f"fairness mismatches: {mismatch}")

# per-task recovery table + token cost
print("\n===== 4. per-task recovery (locked candidates) & token cost =====")
for tid in ["v2_11", "v3_07", "v4_01", "v4_08"]:
    sub = [k for k in locked if k[1] == tid]
    if not sub:
        print(f"{tid}: no locked instances")
        continue
    txt = ", ".join(f"{m.split('_')[1]}="
                    f"{sum(rows[m][k]['success'] for k in sub)}/{len(sub)}"
                    for m in MODES)
    print(f"{tid}: locked n={len(sub)} -> {txt}")
for m in MODES:
    tok = sum(rows[m][k]["total_tokens"] for k in keys) / len(keys)
    print(f"avg tokens {m}: {tok:.0f}")
EOF

echo
echo "===== 5. task matrix (v4) ====="
python -m scripts.task_matrix runs/E4v4
