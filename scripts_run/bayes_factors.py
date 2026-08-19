#!/usr/bin/env python3
"""Bayes factors for §5.6 (honest statistical status).

Method: paired binary outcomes (McNemar discordant pairs b/c).
H0: p=0.5 (no difference); H1: p free, Beta(1,1) prior.
Sequence-level marginal under H1: m1 = b!c!/(b+c+1)!;
under H0: m0 = 2^-(b+c).
BF10 = m1/m0 = b! c! 2^(b+c) / (b+c+1)!.
Recomputed from raw metrics.jsonl (no hand-typed numbers).

Output: analysis/figures_data/bayes_factors.csv
"""
import csv
import json
import math
from pathlib import Path

ROOT = Path("/mnt/g/paper0816")
OUT = ROOT / "analysis" / "figures_data"
OUT.mkdir(parents=True, exist_ok=True)


def bf10(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    log_bf = (math.lgamma(b + 1) + math.lgamma(c + 1)
              + n * math.log(2) - math.lgamma(n + 2))
    return math.exp(log_bf)


def interpret(bf: float) -> str:
    # bf is BF10: >1 favors H1 (difference), <1 favors H0 (no difference)
    if bf > 100:
        return "decisive for H1"
    if bf > 10:
        return "strong for H1"
    if bf > 3:
        return "moderate for H1"
    if bf >= 1 / 3:
        return "inconclusive"
    if bf >= 1 / 10:
        return "moderate for H0"
    if bf >= 1 / 100:
        return "strong for H0"
    return "decisive for H0"


def load_metrics(run: str, seed: int, arm: str) -> dict:
    p = ROOT / "runs" / run / f"seed{seed}" / arm / "metrics.jsonl"
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            out[r["instance_id"]] = r
    return out


def paired_bc(run: str, seeds: list, arm_a: str, arm_b: str,
              lock_on_b: bool = False) -> tuple:
    """b: A wins B loses; c: A loses B wins (unit = task x seed).
    lock_on_b=True keeps only units where B (the structured baseline)
    failed with repetition_events>=2."""
    b = c = n = 0
    for s in seeds:
        ma, mb = load_metrics(run, s, arm_a), load_metrics(run, s, arm_b)
        for t in set(ma) & set(mb):
            if lock_on_b and not ((not mb[t]["success"])
                                  and mb[t].get("repetition_events", 0) >= 2):
                continue
            n += 1
            sa, sb = bool(ma[t]["success"]), bool(mb[t]["success"])
            if sa and not sb:
                b += 1
            elif sb and not sa:
                c += 1
    return b, c, n


results = []

# --- 1. Feedback diagnosticity: repair vs no_feedback ---
# E0 7B (5 seeds, v2 full set)
b, c, n = paired_bc("E0v2s5", [0, 1, 2, 3, 4], "repair", "no_feedback")
results.append(("7B repair vs no_feedback (E0v2s5, feedback content)", b, c, n))
# E6 3B
b, c, n = paired_bc("E6v2", [0, 1, 2, 3, 4], "repair", "no_feedback")
results.append(("3B repair vs no_feedback (E6, R1)", b, c, n))
# retry effect reference: repair vs direct (both models)
b, c, n = paired_bc("E0v2s5", [0, 1, 2, 3, 4], "repair", "direct")
results.append(("7B repair vs direct (retry effect)", b, c, n))
b, c, n = paired_bc("E6v2", [0, 1, 2, 3, 4], "repair", "direct")
results.append(("3B repair vs direct (retry effect)", b, c, n))

# --- 2. Intervention on locked tasks: diverse vs structured ---
for run, model, seeds in [
    ("E4v2lock", "7B", [0]), ("E4v4", "7B", [0]), ("E4v3lock", "7B", [0]),
    ("E5", "7B", [0, 1]), ("E6lock", "3B", [0, 1, 2, 3, 4]),
    ("E6v2", "3B", [0, 1, 2, 3, 4]),
]:
    b, c, n = paired_bc(run, seeds, "repair_diverse", "repair_structured",
                        lock_on_b=True)
    results.append((f"{model} diverse vs structured on locked ({run})", b, c, n))

# --- 3. Attribution: diverse vs weak on locked tasks ---
for run, model, seeds in [
    ("E4v2lock", "7B", [0]), ("E4v4", "7B", [0]), ("E4v3lock", "7B", [0]),
    ("E5", "7B", [0, 1]), ("E6lock", "3B", [0, 1, 2, 3, 4]),
    ("E6v2", "3B", [0, 1, 2, 3, 4]),
]:
    b, c, n = paired_bc(run, seeds, "repair_diverse", "repair_nudge_weak",
                        lock_on_b=True)
    results.append((f"{model} diverse vs weak on locked ({run})", b, c, n))

rows = []
tot_b10 = tot_c10 = 0
# pooled 7B intervention and attribution across runs
pool = {"int7b": [0, 0], "att7b": [0, 0], "int3b": [0, 0]}
for r in results:
    name, b, c, n = r
    bf = bf10(b, c)
    rows.append({"test": name, "b": b, "c": c, "n_units": n,
                 "BF10": round(bf, 4), "BF01": round(1 / bf, 4),
                 "interpretation": interpret(bf)})
    if "7B diverse vs structured" in name:
        pool["int7b"][0] += b
        pool["int7b"][1] += c
    if "3B diverse vs structured" in name:
        pool["int3b"][0] += b
        pool["int3b"][1] += c
    if "7B diverse vs weak" in name:
        pool["att7b"][0] += b
        pool["att7b"][1] += c

for label, key in [("7B POOLED diverse vs structured (locked)", "int7b"),
                   ("3B POOLED diverse vs structured (locked)", "int3b"),
                   ("7B POOLED diverse vs weak (locked)", "att7b")]:
    b, c = pool[key]
    bf = bf10(b, c)
    rows.append({"test": label, "b": b, "c": c, "n_units": b + c,
                 "BF10": round(bf, 4), "BF01": round(1 / bf, 4),
                 "interpretation": interpret(bf)})

with open(OUT / "bayes_factors.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

for r in rows:
    print(f"{r['test']:<58} b/c={r['b']}/{r['c']} n={r['n_units']:<4} "
          f"BF10={r['BF10']:<9} {r['interpretation']}")
