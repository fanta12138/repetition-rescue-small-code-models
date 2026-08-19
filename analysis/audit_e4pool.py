import json, os, hashlib
from collections import defaultdict
from scipy.stats import binom

R = r"g:\paper0816\runs"
SEEDS = range(5)

def load_metrics(root, seed, arm):
    d = {}
    p = os.path.join(root, f"seed{seed}", arm, "metrics.jsonl")
    if not os.path.exists(p):
        return d
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        d[r["instance_id"]] = r
    return d

def traj_hash(root, seed, arm, task):
    p = os.path.join(root, f"seed{seed}", arm, "trajectories.jsonl")
    rows = []
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        if r["instance_id"] == task:
            rows.append(json.dumps({k: r.get(k) for k in ("step", "role", "tool_call", "patch_applied", "completion_tokens", "extra")}, sort_keys=True))
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()

def rep_from_traj(root, seed, arm, task):
    p = os.path.join(root, f"seed{seed}", arm, "trajectories.jsonl")
    ex = []
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        if r["instance_id"] == task and r.get("role") == "coder":
            ex.append(str(r.get("extra")))
    return sum(1 for i in range(1, len(ex)) if ex[i] == ex[i-1])

def is_locked(root, s, arm, task):
    m = load_metrics(root, s, arm).get(task)
    if m is None or m["success"]:
        return False
    rep = m.get("repetition_events")
    if rep is None:
        rep = rep_from_traj(root, s, arm, task)
    return rep >= 2

E4 = [("E4v2lock", "v2_11"), ("E4v3lock", "v3_07")]
locked_all = []  # (run, seed, task, ms_row, md_row, mw_row_or_None)
for run, task in E4:
    root = os.path.join(R, run)
    for s in SEEDS:
        ms = load_metrics(root, s, "repair_structured").get(task)
        if ms and (not ms["success"]) and (ms.get("repetition_events", rep_from_traj(root, s, "repair_structured", task)) >= 2):
            md = load_metrics(root, s, "repair_diverse")[task]
            mw = load_metrics(root, s, "repair_nudge_weak").get(task)
            locked_all.append((run, s, task, ms, md, mw))
root4 = os.path.join(R, "E4v4")
for s in SEEDS:
    ms_all = load_metrics(root4, s, "repair_structured")
    md_all = load_metrics(root4, s, "repair_diverse")
    mw_all = load_metrics(root4, s, "repair_nudge_weak")
    for task, ms in ms_all.items():
        if (not ms["success"]) and ms.get("repetition_events", 0) >= 2:
            locked_all.append(("E4v4", s, task, ms, md_all[task], mw_all.get(task)))

print("total nominal E4 locked:", len(locked_all))
by_task = defaultdict(list)
for run, s, t, *_ in locked_all:
    by_task[t].append((run, s))
for t, v in by_task.items():
    print(" ", t, len(v), sorted(v))

# behavioral units: trajectory hash dedup
hashes = {}
for run, s, t, *_ in locked_all:
    hashes[(run, s, t)] = traj_hash(os.path.join(R, run), s, "repair_structured", t)
unit_map = defaultdict(list)
for k, h in hashes.items():
    unit_map[h].append(k)
print("distinct hashes (behavioral units):", len(unit_map))
for h, ks in unit_map.items():
    print("  ", h[:8], sorted((k[2], k[1]) for k in ks))

b_ds = sum(1 for x in locked_all if x[4]["success"])
print("diverse-vs-structured b/c:", b_ds, "/ 0 of", len(locked_all))
missing_weak = [x for x in locked_all if x[5] is None]
print("missing weak runs:", [(x[0], x[1], x[2]) for x in missing_weak])
paired = [x for x in locked_all if x[5] is not None]
b_dw = sum(1 for x in paired if x[4]["success"] and not x[5]["success"])
c_dw = sum(1 for x in paired if x[5]["success"] and not x[4]["success"])
both = sum(1 for x in paired if x[4]["success"] and x[5]["success"])
print("paired:", len(paired), "diverse-vs-weak b/c:", b_dw, "/", c_dw, "both:", both)

# v2_11 rescue tokens across runs
for run, s, t, ms, md, mw in locked_all:
    if t == "v2_11":
        print("v2_11", run, "s%d" % s, "diverse:", md["success"], md["total_tokens"], md["iterations"],
              "| struct tokens", ms["total_tokens"], "weak:", None if mw is None else mw["success"])

# 10/10 hash identity for v2_11 structured locks (E3v2 + E4v2lock)
h10 = []
for s in SEEDS:
    h10.append(traj_hash(os.path.join(R, "E3v2"), s, "repair_structured", "v2_11"))
for s in SEEDS:
    h10.append(traj_hash(os.path.join(R, "E4v2lock"), s, "repair_structured", "v2_11"))
print("v2_11 structured lock hashes E3v2+E4v2lock:", len(set(h10)), "distinct of 10")

# E3 locked subset token savings (E3v2 v2_11 only)
st = dv = 0
for s in SEEDS:
    ms = load_metrics(os.path.join(R, "E3v2"), s, "repair_structured")["v2_11"]
    md = load_metrics(os.path.join(R, "E3v2"), s, "repair_diverse")["v2_11"]
    st += ms["total_tokens"]; dv += md["total_tokens"]
print("E3 locked subset (v2_11 x5): structured", st, "diverse", dv,
      "savings:", round(100*(1-dv/st), 1), "%")

# E4 locked token savings over 22 nominal
st = sum(x[3]["total_tokens"] for x in locked_all)
dv = sum(x[4]["total_tokens"] for x in locked_all)
print("E4 22-locked token savings: structured", st, "diverse", dv,
      "savings:", round(100*(1-dv/st), 1), "%")

# weak pool n=27
e5_locked = []
root5 = os.path.join(R, "E5")
for s in (0, 1):
    ms_all = load_metrics(root5, s, "repair_structured")
    md_all = load_metrics(root5, s, "repair_diverse")
    mw_all = load_metrics(root5, s, "repair_nudge_weak")
    for task, ms in ms_all.items():
        if (not ms["success"]) and ms.get("repetition_events", rep_from_traj(root5, s, "repair_structured", task)) >= 2:
            e5_locked.append((s, task, ms, md_all[task], mw_all.get(task)))
pool = paired + [x for x in e5_locked if x[4] is not None]
print("weak pool:", len(paired), "(E4 paired) +", len(e5_locked), "(E5) =", len(pool))
wk_resc = sum(1 for x in pool if x[4 if len(x)==5 else 5] if False)
wk_resc = sum(1 for x in pool if (x[5] if len(x) > 5 else x[4]) and (x[5] if len(x) > 5 else x[4])["success"])
print("weak rescues in pool:", wk_resc, "/", len(pool),
      [(x[0], x[1], x[2]) for x in pool if (x[5] if len(x) > 5 else x[4]) and (x[5] if len(x) > 5 else x[4])["success"]])
