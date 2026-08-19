#!/usr/bin/env bash
# E6 preregistered analysis: R1 feedback-diagnosticity replication,
# lock identification, R3 intervention main test, R2 attribution,
# fairness + regression guards, and the v4_08 benchmark.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816

python - <<'EOF'
import hashlib, json, math
from pathlib import Path

ARMS6 = ["direct", "repair", "no_feedback", "repair_structured",
         "repair_diverse", "repair_nudge_weak"]
SEEDS = [0, 1, 2, 3, 4]

def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)

rows = {}   # (task, seed) -> arm -> metrics row
traj = {}   # (task, seed) -> arm -> hash of concatenated coder excerpts
for seed in SEEDS:
    for arm in ARMS6:
        for line in Path(f"runs/E6v2/seed{seed}/{arm}/metrics.jsonl").read_text().splitlines():
            r = json.loads(line)
            rows.setdefault((r["instance_id"], seed), {})[arm] = r
for seed in SEEDS:
    for arm in ["repair_structured", "repair_diverse", "repair_nudge_weak"]:
        ex = {}
        for line in Path(f"runs/E6v2/seed{seed}/{arm}/trajectories.jsonl").read_text().splitlines():
            t = json.loads(line)
            if t["role"] == "coder":
                ex.setdefault(t["instance_id"], []).append(t["extra"]["response_excerpt"])
        for tid, lst in ex.items():
            traj.setdefault((tid, seed), {})[arm] = hashlib.md5("\n---\n".join(lst).encode()).hexdigest()

tasks = sorted({k[0] for k in rows})

# ---------- R1: feedback diagnosticity replication ----------
print("=== R1: arm success rates (n=100 each) ===")
rate = {}
for arm in ARMS6:
    s = sum(1 for tid in tasks for seed in SEEDS if rows[(tid, seed)][arm]["success"])
    rate[arm] = s
    tok = sum(rows[(tid, seed)][arm]["total_tokens"] for tid in tasks for seed in SEEDS) / 100
    print(f"{arm:20} {s}/100  avg_tokens={tok:.0f}")

def pair_test(a, b):
    disc_b = disc_c = 0
    for tid in tasks:
        for seed in SEEDS:
            sa, sb = rows[(tid, seed)][a]["success"], rows[(tid, seed)][b]["success"]
            if sa and not sb: disc_b += 1
            if sb and not sa: disc_c += 1
    return disc_b, disc_c, mcnemar(disc_b, disc_c)

for a, b in [("repair", "no_feedback"), ("repair", "direct"),
             ("repair_structured", "no_feedback"),
             ("repair_diverse", "no_feedback")]:
    bb, cc, p = pair_test(a, b)
    d = (rate[a] - rate[b])
    print(f"{a} vs {b}: d={d:+d}pp b/c={bb}/{cc} p={p:.4f}")
d_rf = rate["repair"] - rate["no_feedback"]
d_rd = rate["repair"] - rate["direct"]
print(f"R1 verdict: {'REPLICATED' if (d_rf <= 3 and d_rd > 0) else 'NOT replicated'}"
      f" (repair-no_feedback={d_rf:+d}pp, repair-direct={d_rd:+d}pp)")

# ---------- Lock identification (structured arm) ----------
locked = []
for tid in tasks:
    if all((not rows[(tid, s)]["repair_structured"]["success"])
           and rows[(tid, s)]["repair_structured"]["repetition_events"] >= 2
           for s in SEEDS):
        locked.append(tid)
print(f"\n=== Locked tasks (structured fail + rep>=2, all 5 seeds) ===\n{locked or 'NONE'}")

# determinism across seeds for locked tasks
units = []
for tid in locked:
    hs = {traj[(tid, s)]["repair_structured"] for s in SEEDS}
    print(f"{tid}: {len(hs)} distinct structured trajectories over 5 seeds")
    units.extend([(tid, s) for s in SEEDS] if len(hs) > 1 else [(tid, 0)])
print(f"independent locked units K = {len(units)}")

# ---------- R3: diverse vs structured on locked units ----------
def arm_on_units(arm):
    wins, losses = 0, 0
    detail = []
    for tid, seed in units:
        s = rows[(tid, seed)]["repair_structured"]["success"]
        x = rows[(tid, seed)][arm]["success"]
        if x and not s: wins += 1
        if s and not x: losses += 1
        detail.append((tid, seed, s, x))
    return wins, losses, detail

if units:
    b3, c3, det3 = arm_on_units("repair_diverse")
    p3 = mcnemar(b3, c3)
    print(f"\n=== R3: diverse vs structured (K={len(units)}) b/c={b3}/{c3} p={p3:.4f} "
          f"-> {'SIGNIFICANT (b>=7,c=0)' if (b3 >= 7 and c3 == 0) else 'threshold not met'}")
    for tid, seed, s, x in det3:
        print(f"  {tid}@{seed}: structured={int(s)} diverse={int(x)}")
    b2, c2, det2 = arm_on_units("repair_nudge_weak")
    print(f"=== R2: weak vs structured b/c={b2}/{c2} ===")
    # diverse vs weak
    bw = cw = 0
    for tid, seed in units:
        d = rows[(tid, seed)]["repair_diverse"]["success"]
        w = rows[(tid, seed)]["repair_nudge_weak"]["success"]
        if d and not w: bw += 1
        if w and not d: cw += 1
    print(f"=== diverse vs weak b/c={bw}/{cw} p={mcnemar(bw, cw):.4f}")

# ---------- fairness + regression guards ----------
print("\n=== Fairness: rep=0 instances, tokens equal across loop arms ===")
mism = 0
for tid in tasks:
    for seed in SEEDS:
        r = rows[(tid, seed)]
        if r["repair_structured"]["repetition_events"] == 0:
            t = {a: r[a]["total_tokens"] for a in ["repair_structured", "repair_diverse", "repair_nudge_weak"]}
            if len(set(t.values())) > 1:
                mism += 1
                print(f"MISMATCH {tid}@{seed}: {t}")
print(f"fairness mismatches: {mism}")

print("\n=== Regression guard: non-locked instances ===")
for arm in ["repair_diverse", "repair_nudge_weak"]:
    loss = gain = 0
    for tid in tasks:
        if tid in locked:
            continue
        for seed in SEEDS:
            s = rows[(tid, seed)]["repair_structured"]["success"]
            x = rows[(tid, seed)][arm]["success"]
            if s and not x: loss += 1
            if x and not s: gain += 1
    print(f"{arm} vs structured (non-locked): gain={gain} loss={loss}")

# ---------- v4_08 benchmark ----------
print("\n=== E6lock: v4_08 under 3 loop arms ===")
r4 = {}
for seed in SEEDS:
    for arm in ["repair_structured", "repair_diverse", "repair_nudge_weak"]:
        p = Path(f"runs/E6lock/seed{seed}/{arm}/metrics.jsonl")
        if p.exists():
            for line in p.read_text().splitlines():
                r = json.loads(line)
                r4.setdefault(arm, []).append(r)
for arm, lst in r4.items():
    s = sum(int(r["success"]) for r in lst)
    reps = ",".join(str(r["repetition_events"]) for r in lst)
    print(f"{arm:20} {s}/{len(lst)}  reps=[{reps}]")
EOF
