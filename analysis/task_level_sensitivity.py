# Task-level sensitivity analysis for E0 (v2, 5 seeds x 20 tasks).
# The preregistered primary analysis uses task x seed instances (n=100/arm).
# This sensitivity check aggregates to the task level (n=20) to bound the
# effect of cross-seed dependence under low-temperature decoding.
import json, itertools, math
from pathlib import Path

ROOT = Path(r"g:\paper0816\runs\E0v2s5")
ARMS = ["direct", "repair", "no_feedback", "random_reflection"]
SEEDS = range(5)

def load(arm):
    # task -> seed -> success bool
    d = {}
    for s in SEEDS:
        p = ROOT / f"seed{s}" / arm / "metrics.jsonl"
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            d.setdefault(r["instance_id"], {})[s] = bool(r["success"])
    return d

data = {a: load(a) for a in ARMS}
tasks = sorted(data["direct"])

print("== per-task cross-seed consistency (all 5 seeds agree?) ==")
for arm in ARMS:
    n_agree = sum(1 for t in tasks if len(set(data[arm][t].values())) == 1)
    print(f"{arm:18s}: {n_agree}/20 tasks fully consistent across seeds")

def task_majority(d, t):
    vals = list(d[t].values())
    return sum(vals) > len(vals) / 2

def task_any(d, t):
    return any(d[t].values())

def mcnemar(a, b, agg, label):
    # paired task-level: nB = a-success & b-fail; nC = a-fail & b-success
    bc = [(agg(a, t), agg(b, t)) for t in tasks]
    nB = sum(1 for x, y in bc if x and not y)
    nC = sum(1 for x, y in bc if not x and y)
    n = nB + nC
    m = min(nB, nC)
    p = min(1.0, 2 * 0.5 ** n * sum(math.comb(n, k) for k in range(0, m + 1))) if n else float("nan")
    sa = sum(1 for t in tasks if agg(a, t)); sb = sum(1 for t in tasks if agg(b, t))
    print(f"{label:38s}: A={sa}/20 B={sb}/20 | b/c={nB}/{nC} p={p:.4f}")

print("\n== task-level paired tests (n=20 tasks) ==")
mcnemar(data["repair"], data["direct"], task_majority, "repair vs direct")
mcnemar(data["repair"], data["no_feedback"], task_majority, "repair vs no_feedback")
mcnemar(data["no_feedback"], data["direct"], task_majority, "no_feedback vs direct")
mcnemar(data["repair"], data["direct"], task_any, "repair vs direct (any-seed)")
mcnemar(data["repair"], data["no_feedback"], task_any, "repair vs no_feedback (any-seed)")
