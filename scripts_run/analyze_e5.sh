#!/usr/bin/env bash
# E5 analysis (preregistered): task-unit tests on locked units +
# mechanistic inspection of what diverse did after the nudge fired.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816

python - <<'EOF'
import json
from pathlib import Path

ARM = ["repair_structured", "repair_diverse", "repair_nudge_weak"]
rows = {}
for seed in [0, 1]:
    for m in ARM:
        for line in Path(f"runs/E5/seed{seed}/{m}/metrics.jsonl").read_text().splitlines():
            r = json.loads(line)
            rows.setdefault((r["instance_id"], seed), {})[m] = r

print("=== per-instance outcomes (locked subset) ===")
print(f"{'task':8} {'seed':4} | structured | diverse | weak")
for (tid, seed) in sorted(rows):
    o = rows[(tid, seed)]
    fmt = lambda r: f"{'PASS' if r['success'] else 'FAIL'}/r{r['repetition_events']}/i{r['interventions']}/{r['total_tokens']}"
    print(f"{tid:8} {seed:4} | {fmt(o['repair_structured']):18} | {fmt(o['repair_diverse']):18} | {fmt(o['repair_nudge_weak']):18}")

# Preregistered units: v5_07@0, v5_07@1, v5_09@0, v5_09@1 (deterministic),
# v5_04@seed1 (verbatim lock). v5_04@seed0 is drift -> excluded per prereg.
units = [("v5_04", 1), ("v5_07", 0), ("v5_07", 1), ("v5_09", 0), ("v5_09", 1)]
# collapse deterministic duplicates
seen, uniq = set(), []
for u in units:
    key = u[0] if u[0] != "v5_04" else ("v5_04", u[1])
    if key not in seen:
        seen.add(key)
        uniq.append(u)
print("\n=== preregistered unique locked units ===", uniq)
for arm in ["repair_diverse", "repair_nudge_weak"]:
    b = sum(1 for u in uniq if rows[u]["repair_diverse" if arm == "repair_diverse" else "repair_nudge_weak"]["success"]
            and not rows[u]["repair_structured"]["success"])
    c = sum(1 for u in uniq if not rows[u]["repair_diverse" if arm == "repair_diverse" else "repair_nudge_weak"]["success"]
            and rows[u]["repair_structured"]["success"])
    print(f"{arm} vs structured: b={b} c={c}")

# determinism check within E5 vs screen (structured)
print("\n=== structured determinism: E5 vs E5_screen token match ===")
for seed in [0, 1]:
    for line in Path(f"runs/E5_screen/seed{seed}/repair_structured/metrics.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["instance_id"] in ("v5_04", "v5_07", "v5_09"):
            r2 = rows[(r["instance_id"], seed)]["repair_structured"]
            same = r["total_tokens"] == r2["total_tokens"]
            print(f"{r['instance_id']} seed{seed}: screen={r['total_tokens']} e5={r2['total_tokens']} {'SAME' if same else 'DIFF'}")

# mechanistic: what did diverse output right after the nudge fired?
print("\n=== diverse post-nudge code (step after intervention) ===")
for seed in [0, 1]:
    steps = {}
    for line in Path(f"runs/E5/seed{seed}/repair_diverse/trajectories.jsonl").read_text().splitlines():
        t = json.loads(line)
        steps.setdefault(t["instance_id"], []).append(t)
    for tid in ("v5_04", "v5_07", "v5_09"):
        ss = [t for t in steps[tid] if t["role"] == "coder"]
        print(f"--- {tid} seed{seed}: {len(ss)} coder steps ---")
        # last coder step is the post-nudge attempt if interventions>0
        last = ss[-1]["extra"]["response_excerpt"]
        print(last[:400].replace("\n", "\\n")[:400])
        print()
EOF
