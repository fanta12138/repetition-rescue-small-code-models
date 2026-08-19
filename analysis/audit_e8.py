import json, os, hashlib, itertools
from scipy.stats import binom, beta as beta_dist

ROOT = r"g:\paper0816\runs\E8"
ARMS = ["direct", "repair_structured", "repair_diverse", "repair_nudge_weak"]
SEEDS = range(5)

def load_metrics(arm, seed):
    d = {}
    p = os.path.join(ROOT, f"seed{seed}", arm, "metrics.jsonl")
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        d[r["instance_id"]] = r
    return d

def load_traj(arm, seed):
    d = {}
    p = os.path.join(ROOT, f"seed{seed}", arm, "trajectories.jsonl")
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        key = json.dumps({k: r.get(k) for k in ("step", "role", "tool_call", "patch_applied", "completion_tokens", "extra")}, sort_keys=True)
        d.setdefault(r["instance_id"], []).append(key)
    return {k: hashlib.sha256("\n".join(v).encode()).hexdigest() for k, v in d.items()}

M = {arm: {s: load_metrics(arm, s) for s in SEEDS} for arm in ARMS}
print("=== Claim 1: arm pass rates ===")
for arm in ARMS:
    tot = sum(m["success"] for s in SEEDS for m in M[arm][s].values())
    n = sum(len(M[arm][s]) for s in SEEDS)
    print(arm, tot, "/", n, "=", round(100*tot/n, 2), "%")

print("\n=== Claim 2: P1 prevalence (structured fail & rep>=2) ===")
locked = []  # (task, seed, metrics_row)
for s in SEEDS:
    for task, r in M["repair_structured"][s].items():
        if (not r["success"]) and r["repetition_events"] >= 2:
            locked.append((task, s))
n_tot = 820
k = len(locked)
ci_lo = beta_dist.ppf(0.025, k, n_tot - k + 1) * 100
ci_hi = beta_dist.ppf(0.975, k + 1, n_tot - k) * 100
tasks = sorted(set(t for t, s in locked))
print("locked:", k, "/", n_tot, "=", round(100*k/n_tot, 2), "%")
print(f"Clopper-Pearson 95% CI: [{ci_lo:.2f}, {ci_hi:.2f}]")
print("distinct tasks:", len(tasks))

T = {arm: {s: load_traj(arm, s) for s in SEEDS} for arm in ["repair_structured"]}
hashes = set()
for t, s in locked:
    hashes.add(T["repair_structured"][s][t])
print("distinct structured trajectory hashes among locked:", len(hashes))

print("\n=== Claim 3: S1 structured vs direct ===")
b = c = 0
for s in SEEDS:
    for task in M["direct"][s]:
        st = M["repair_structured"][s][task]["success"]
        di = M["direct"][s][task]["success"]
        if st and not di: b += 1
        if di and not st: c += 1
p_s1 = min(1.0, 2 * binom.cdf(min(b, c), b + c, 0.5)) if b + c else 1.0
ps = sum(m["success"] for s in SEEDS for m in M["repair_structured"][s].values())
pd_ = sum(m["success"] for s in SEEDS for m in M["direct"][s].values())
print("structured", ps, "direct", pd_, "Delta =", round(100*(ps-pd_)/820, 2), "pp; b/c =", b, "/", c, "; p =", round(p_s1, 4))

print("\n=== Claim 4: P2/P3 on locked units ===")
locked_set = set(locked)
div_rescue = [(t, s) for t, s in locked if M["repair_diverse"][s][t]["success"]]
weak_rescue = [(t, s) for t, s in locked if M["repair_nudge_weak"][s][t]["success"]]
print("diverse rescues:", len(div_rescue), "/", k)
print("weak rescues:", len(weak_rescue), "/", k, weak_rescue)
b = c = 0
for t, s in locked:
    dv = M["repair_diverse"][s][t]["success"]
    wk = M["repair_nudge_weak"][s][t]["success"]
    if dv and not wk: b += 1
    if wk and not dv: c += 1
p_p3 = min(1.0, 2 * binom.cdf(min(b, c), b + c, 0.5)) if b + c else 1.0
delta = 100 * (len(div_rescue) - len(weak_rescue)) / k
print("diverse-vs-weak on locked: b/c =", b, "/", c, "p =", p_p3, "Delta = %.2f pp" % delta)

print("\n=== Claim 5: S2 determinism ===")
from collections import defaultdict
by_task = defaultdict(list)
for t, s in locked:
    by_task[t].append(s)
multi = {t: sorted(ss) for t, ss in by_task.items() if len(ss) >= 2}
print("tasks locked on >=2 seeds:", len(multi))
ident = 0
for t, ss in multi.items():
    hs = {T["repair_structured"][s][t] for s in ss}
    if len(hs) == 1: ident += 1
print("of those, byte-identical trajectories across locked seeds:", ident,
      "=", round(100*ident/len(multi), 1), "%")

print("\n=== Claim 6: interim cross-seed identity seeds 0-1 ===")
same = tot = 0
for arm in ARMS:
    for task in M[arm][0]:
        h0 = T_all = None
tot = same = 0
TA = {arm: {s: load_traj(arm, s) for s in SEEDS} for arm in ARMS}
for arm in ARMS:
    a = b_ = 0
    for task in TA[arm][0]:
        tot += 1
        if TA[arm][0][task] == TA[arm][1][task]:
            same += 1
            a += 1
        b_ += 1
    print(arm, "identity seed0-seed1:", a, "/", b_)
print("overall:", same, "/", tot, "=", round(100*same/tot, 1), "%")
