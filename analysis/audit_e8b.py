import json, os, hashlib
from collections import defaultdict

ROOT = r"g:\paper0816\runs\E8"
ARMS = ["direct", "repair_structured", "repair_diverse", "repair_nudge_weak"]

def load_traj(seed, arm):
    d = {}
    p = os.path.join(ROOT, f"seed{seed}", arm, "trajectories.jsonl")
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        key = json.dumps({k: r.get(k) for k in ("step", "role", "tool_call", "patch_applied", "completion_tokens", "extra")}, sort_keys=True)
        d.setdefault(r["instance_id"], []).append(key)
    return {k: hashlib.sha256("\n".join(v).encode()).hexdigest() for k, v in d.items()}

T = {(s, a): load_traj(s, a) for s in range(5) for a in ARMS}
tasks = sorted(T[(0, ARMS[0])].keys())

# A: per task, all 20 trajectories identical (all arms x seeds 0,1)
cA = sum(1 for t in tasks if len({T[(s, a)][t] for s in (0, 1) for a in ARMS}) == 1)
# B: per task-arm, seed0==seed1 (4 arms), count tasks where ALL arms identical
okall = sum(1 for t in tasks if all(T[(0, a)][t] == T[(1, a)][t] for a in ARMS))
okany = sum(1 for t in tasks if any(T[(0, a)][t] == T[(1, a)][t] for a in ARMS))
# D: tasks where identical in at least 2 arms
ok2 = sum(1 for t in tasks if sum(T[(0, a)][t] == T[(1, a)][t] for a in ARMS) >= 2)
print("A all20:", cA, "/164 =", round(100*cA/164, 1))
print("B task all-arms:", okall, "/164 =", round(100*okall/164, 1))
print("B2 any arm:", okany, "/164 =", round(100*okany/164, 1))
print("D >=2 arms:", ok2, "/164 =", round(100*ok2/164, 1))
# loop arms only (3), per task all identical
LOOP = ARMS[1:]
okloop = sum(1 for t in tasks if all(T[(0, a)][t] == T[(1, a)][t] for a in LOOP))
pairloop = sum(1 for t in tasks for a in LOOP if T[(0, a)][t] == T[(1, a)][t])
print("loop all-arms task:", okloop, "/164 =", round(100*okloop/164, 1))
print("loop pairs:", pairloop, "/", 164*3, "=", round(100*pairloop/492, 1))
