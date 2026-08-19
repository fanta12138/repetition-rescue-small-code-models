import json, os, hashlib
from collections import defaultdict
from scipy.stats import binom

R = r"g:\paper0816\runs"

def load_metrics(root, seed, arm):
    d = {}
    p = os.path.join(root, f"seed{seed}", arm, "metrics.jsonl")
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        d[r["instance_id"]] = r
    return d

def load_traj(root, seed, arm):
    d = {}
    p = os.path.join(root, f"seed{seed}", arm, "trajectories.jsonl")
    if not os.path.exists(p):
        return {}
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        key = json.dumps({k: r.get(k) for k in ("step", "role", "tool_call", "patch_applied", "completion_tokens", "extra")}, sort_keys=True)
        d.setdefault(r["instance_id"], []).append(key)
    return {k: hashlib.sha256("\n".join(v).encode()).hexdigest() for k, v in d.items()}

def rep_from_traj(root, seed, arm, task):
    """count verbatim repetition events among coder completions"""
    p = os.path.join(root, f"seed{seed}", arm, "trajectories.jsonl")
    ex = []
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        if r["instance_id"] == task and r.get("role") == "coder":
            ex.append(str(r.get("extra")))
    return sum(1 for i in range(1, len(ex)) if ex[i] == ex[i-1]), len(ex)

SEEDS = range(5)

print("=== Claim 7: E3v2+E3v3 pooled ===")
for root in (R + r"\E3v2", R + r"\E3v3"):
    arms = os.listdir(os.path.join(root, "seed0"))
    print(os.path.basename(root), "arms:", arms)
st = dv = {}
structured_pass = diverse_pass = n = 0
locked_e3 = []
hashes = []
for root in (R + r"\E3v2", R + r"\E3v3"):
    for s in SEEDS:
        ms = load_metrics(root, s, "repair_structured")
        md = load_metrics(root, s, "repair_diverse")
        ts = load_traj(root, s, "repair_structured")
        for task in ms:
            n += 1
            structured_pass += ms[task]["success"]
            diverse_pass += md[task]["success"]
            rep = ms[task].get("repetition_events")
            if rep is None:
                rep, _nc = rep_from_traj(root, s, "repair_structured", task)
            if (not ms[task]["success"]) and rep >= 2:
                locked_e3.append((os.path.basename(root), s, task, ms[task], md[task]))
                hashes.append(ts.get(task))
print("pooled n:", n, "structured:", structured_pass, "diverse:", diverse_pass,
      "Delta:", round(100*(diverse_pass-structured_pass)/n, 2), "pp")
print("locked:", [(x[0], x[1], x[2]) for x in locked_e3])
b = sum(1 for x in locked_e3 if x[4]["success"])
print("diverse rescues locked:", b, "/", len(locked_e3),
      "p =", 2*binom.sf(b-1, len(locked_e3), 0.5) if locked_e3 else None)
print("distinct locked hashes (per run):", len(set(hashes)),
      "unique hash across all:", len(set(hashes)) == 1)
st_tok = sum(x[3]["total_tokens"] for x in locked_e3)
dv_tok = sum(x[4]["total_tokens"] for x in locked_e3)
print("E3 locked token savings: structured", st_tok, "diverse", dv_tok,
      "savings:", round(100*(1-dv_tok/st_tok), 1), "%")

print("\n=== Claim 8/9/13: E4v4 ===")
root = R + r"\E4v4"
locked_e4 = []
allm = {}
for s in SEEDS:
    ms = load_metrics(root, s, "repair_structured")
    md = load_metrics(root, s, "repair_diverse")
    mw = load_metrics(root, s, "repair_nudge_weak")
    ts = load_traj(root, s, "repair_structured")
    allm[s] = (ms, md, mw)
    for task in ms:
        if (not ms[task]["success"]) and ms[task]["repetition_events"] >= 2:
            locked_e4.append((s, task, ms[task], md[task], mw.get(task), ts.get(task)))
print("nominal locked:", len(locked_e4))
by_task = defaultdict(list)
for s, t, ms, md, mw, h in locked_e4:
    by_task[t].append(s)
print("by task:", dict(by_task))
print("distinct trajectory hashes (units):", len({h for *_, h in locked_e4}))
b_ds = sum(1 for x in locked_e4 if x[3]["success"])
print("diverse-vs-structured b/c on locked:", b_ds, "/", 0)
paired = [x for x in locked_e4 if x[4] is not None]
print("with paired weak:", len(paired))
b_dw = sum(1 for x in paired if x[3]["success"] and not x[4]["success"])
c_dw = sum(1 for x in paired if x[4]["success"] and not x[3]["success"])
print("diverse-vs-weak b/c:", b_dw, "/", c_dw)
for task in ("v2_11", "v4_08", "v4_04", "v3_07", "v4_01", "v4_05"):
    xs = [x for x in locked_e4 if x[1] == task]
    resc = [x[0] for x in xs if x[3]["success"]]
    wk = [x[0] for x in xs if x[4] and x[4]["success"]]
    toks = {x[0]: x[3]["total_tokens"] for x in xs if x[3]["success"]}
    its = {x[0]: x[3]["iterations"] for x in xs if x[3]["success"]}
    print(task, "locked seeds:", [x[0] for x in xs], "diverse rescues:", resc,
          "weak rescues:", wk, "rescue tokens:", set(toks.values()), "iters:", set(its.values()))
st_tok = sum(x[2]["total_tokens"] for x in locked_e4)
dv_tok = sum(x[3]["total_tokens"] for x in locked_e4)
print("E4 locked token savings: structured", st_tok, "diverse", dv_tok,
      "savings:", round(100*(1-dv_tok/st_tok), 1), "%")
print("structured iters on locked:", {x[2]["iterations"] for x in locked_e4})

print("\n=== E5 screen ===")
root = R + r"\E5"
for s in sorted(os.listdir(root)):
    if not s.startswith("seed"): continue
    ms = load_metrics(root, int(s[4:]), "repair_structured")
    md = load_metrics(root, int(s[4:]), "repair_diverse")
    mw = load_metrics(root, int(s[4:]), "repair_nudge_weak")
    for task in ms:
        rep = ms[task].get("repetition_events")
        if rep is None:
            rep, _x = rep_from_traj(root, int(s[4:]), "repair_structured", task)
        if (not ms[task]["success"]) and rep >= 2:
            print(s, task, "rep=", rep,
                  "diverse:", md[task]["success"], "weak:", mw[task]["success"])

print("\n=== Claim 11: E6lock v4_08 at 3B ===")
root = R + r"\E6lock"
for arm in ("repair_structured", "repair_diverse", "repair_nudge_weak"):
    succ = []
    reps = []
    toks = []
    for s in SEEDS:
        m = load_metrics(root, s, arm)
        for task, r in m.items():
            rep = r.get("repetition_events")
            if rep is None:
                rep, _x = rep_from_traj(root, s, arm, task)
            succ.append(r["success"])
            reps.append(rep)
            toks.append((s, task, r["success"], r["total_tokens"]))
    print(arm, "success:", sum(succ), "/5", "rep:", reps)
    print("  per-seed tokens:", toks)

print("\n=== Claim 12: weak pool ===")
# 7B locked instances with weak runs: E4v4 locked (weak), E5 locked (weak), E3 locked?
pool = [(x[1], x[0]) for x in locked_e4 if x[4] is not None]
print("E4v4 locked with weak:", len(pool))
