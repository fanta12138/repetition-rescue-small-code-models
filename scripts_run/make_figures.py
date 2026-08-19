#!/usr/bin/env python3
"""Paper figures (matplotlib, Times New Roman) + paired CSV data sources.

Fig 1: success rate by arm, 7B vs 3B (feedback dissection).
Fig 2: locked-unit x arm rescue matrix (heatmap) with token cost.
Fig 3: AST structural distance trajectories for the three typology classes.

Outputs to figures/: figN_name.pdf/.png and figN_name.csv.
All numbers recomputed from runs/* metrics.jsonl / figures_data CSVs.
"""
import csv
import json
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

ROOT = Path("/mnt/g/paper0816")
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    "mathtext.fontset": "stix",
    "font.size": 9,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "lines.linewidth": 1.2,
    "pdf.fonttype": 42,  # editable text in Illustrator/Visio imports
    "ps.fonttype": 42,
})


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def bf10(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return math.exp(math.lgamma(b + 1) + math.lgamma(c + 1)
                    + n * math.log(2) - math.lgamma(n + 2))


def load_metrics(run, seed, arm):
    p = ROOT / "runs" / run / f"seed{seed}" / arm / "metrics.jsonl"
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            out[r["instance_id"]] = r
    return out


ARMS = ["direct", "repair", "no_feedback", "repair_structured",
        "repair_diverse", "repair_nudge_weak"]
ARM_LABEL = {"direct": "direct", "repair": "repair\n(full fb)",
             "no_feedback": "retry only\n(no fb)",
             "repair_structured": "structured",
             "repair_diverse": "diverse\n(+nudge)",
             "repair_nudge_weak": "weak\n(+nudge)"}

# Per-model x arm source mapping (7B weak arm only ever ran on lock subset).
SOURCES = {
    "7B-AWQ": {
        "direct": [("E0v2s5", range(5))],
        "repair": [("E0v2s5", range(5))],
        "no_feedback": [("E0v2s5", range(5))],
        "repair_structured": [("E3v2", range(5))],
        "repair_diverse": [("E3v2", range(5))],
        "repair_nudge_weak": [("E4v2lock", range(5)), ("E4v3lock", range(5)),
                              ("E4v4", range(5)), ("E5", range(2))],
    },
    "3B-AWQ": {a: [("E6v2", range(5))] for a in ARMS},
}


def is_locked(row):
    return (not row["success"]) and row.get("repetition_events", 0) >= 2


# 7B weak arm only ran inside intervention screens -> pool over locked
# instances only (same lock criterion as Fig 2) to stay comparable.
def weak_7b_locked():
    ok = tot = toks = 0
    seen = set()
    for run, seeds in SOURCES["7B-AWQ"]["repair_nudge_weak"]:
        for s in seeds:
            struct = load_metrics(run, s, "repair_structured")
            weak = load_metrics(run, s, "repair_nudge_weak")
            for tid, row in weak.items():
                if tid not in struct or not is_locked(struct[tid]):
                    continue
                key = (run, s, tid)
                if key in seen:
                    continue
                seen.add(key)
                tot += 1
                ok += int(bool(row["success"]))
                toks += row["total_tokens"]
    return ok, tot, toks

# ---------------- Fig 1: success rate by arm ----------------
rows1 = []
stats = {}
for model in ["7B-AWQ", "3B-AWQ"]:
    per = {}
    for arm in ARMS:
        if model == "7B-AWQ" and arm == "repair_nudge_weak":
            ok, tot, toks = weak_7b_locked()
        else:
            ok = tot = toks = 0
            for run, seeds in SOURCES[model][arm]:
                for s in seeds:
                    for r in load_metrics(run, s, arm).values():
                        tot += 1
                        ok += int(bool(r["success"]))
                        toks += r["total_tokens"]
        per[arm] = (ok, tot, toks / max(tot, 1))
        subset = model == "7B-AWQ" and arm == "repair_nudge_weak"
        rows1.append({"model": model, "arm": arm, "success": ok,
                      "n": tot, "success_rate": round(ok / max(tot, 1), 4),
                      "avg_tokens": round(toks / max(tot, 1), 1),
                      "subset": "lock-only" if subset else "full-v2"})
    stats[model] = per

fig, ax = plt.subplots(figsize=(6.5, 2.6))
x = range(len(ARMS))
w = 0.36
for i, model in enumerate(["7B-AWQ", "3B-AWQ"]):
    rates = [stats[model][a][0] / max(stats[model][a][1], 1) for a in ARMS]
    bars = ax.bar([xi + (i - 0.5) * w for xi in x], rates, w,
                  color=["#444444", "#d6604d"][i], edgecolor="black",
                  linewidth=0.5, label=model)
    for bar, a in zip(bars, ARMS):
        if model == "7B-AWQ" and a == "repair_nudge_weak":
            bar.set_hatch("////")  # lock-subset estimate, not full v2
    for xi, a in zip(x, ARMS):
        r, n = stats[model][a][0] / max(stats[model][a][1], 1), stats[model][a][1]
        star = "*" if (model == "7B-AWQ" and a == "repair_nudge_weak") else ""
        ax.text(xi + (i - 0.5) * w, r + 0.012, f"{r:.0%}{star}\nn={n}",
                ha="center", fontsize=6, va="bottom")
# significance annotations (repair vs no_feedback), sources per model
for model, xi_pair in [("7B-AWQ", (1, 2)), ("3B-AWQ", (1, 2))]:
    b = c = 0
    run = "E0v2s5" if model == "7B-AWQ" else "E6v2"
    for s in range(5):
        ma = load_metrics(run, s, "repair")
        mb = load_metrics(run, s, "no_feedback")
        for t in set(ma) & set(mb):
            sa, sb = bool(ma[t]["success"]), bool(mb[t]["success"])
            b += sa and not sb
            c += sb and not sa
    p, bf = mcnemar_exact(b, c), bf10(b, c)
    xi = (xi_pair[0] + xi_pair[1]) / 2
    off = -0.5 if model == "7B-AWQ" else 0.5
    ax.annotate(f"repair vs no-fb:\np={p:.3f}, BF$_{{10}}$={bf:.1f}",
                xy=(xi + off * w, 0.985), fontsize=6.2, ha="center",
                color=["#444444", "#d6604d"][0 if model == "7B-AWQ" else 1])
ax.set_xticks(list(x))
ax.set_xticklabels([ARM_LABEL[a] for a in ARMS], fontsize=7.5)
ax.set_ylabel("success rate")
ax.set_ylim(0, 1.18)
ax.legend(fontsize=8, frameon=False, loc="upper left", ncols=2)
ax.set_title("Feedback dissection: gains come from retry, not diagnostic "
             "content (7B); 3B shows a boundary effect\n"
             f"* 7B weak arm measured on locked units only "
             f"(n={stats['7B-AWQ']['repair_nudge_weak'][1]})",
             fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "fig1_feedback_dissection.pdf")
fig.savefig(FIG / "fig1_feedback_dissection.png", dpi=200)
with open(FIG / "fig1_feedback_dissection.csv", "w", newline="") as f:
    wcsv = csv.DictWriter(f, fieldnames=list(rows1[0].keys()))
    wcsv.writeheader()
    wcsv.writerows(rows1)

# ---------------- Fig 2: locked-unit x arm rescue matrix ----------------
LOCK_SOURCES = [
    ("7B", "E4v2lock", list(range(5))), ("7B", "E4v4", list(range(5))),
    ("7B", "E4v3lock", list(range(5))),
    ("7B", "E5", [0, 1]),
    ("3B", "E6lock", list(range(5))), ("3B", "E6v2", list(range(5))),
]
units = []  # (label, arm -> (success, tokens))
for model, run, seeds in LOCK_SOURCES:
    for s in seeds:
        base = load_metrics(run, s, "repair_structured")
        arms_data = {a: load_metrics(run, s, a) for a in
                     ["repair_structured", "repair_diverse",
                      "repair_nudge_weak"]}
        for tid, row in sorted(base.items()):
            if row["success"] or row.get("repetition_events", 0) < 2:
                continue
            entry = {}
            for a, data in arms_data.items():
                r = data.get(tid)
                entry[a] = (int(bool(r["success"])) if r else None,
                            r["total_tokens"] if r else None)
            units.append((f"{model} {tid} s{s}", entry))

dedup_labels = []
rows2 = []
for label, entry in units:
    short = label.replace("repair_", "")
    for a in ["repair_structured", "repair_diverse", "repair_nudge_weak"]:
        ok, tk = entry[a]
        rows2.append({"unit": label, "arm": a, "success": ok, "tokens": tk})
    dedup_labels.append(label)

mat = [[entry[a][0] for a in ["repair_structured", "repair_diverse",
                              "repair_nudge_weak"]] for _, entry in units]
import numpy as np
M = np.array(mat, dtype=float)
fig, ax = plt.subplots(figsize=(3.6, max(3.0, 0.24 * len(units) + 1)))
im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(3))
ax.set_xticklabels(["structured\n(baseline)", "diverse\n(+nudge)",
                    "weak\n(+nudge)"], fontsize=7.5)
ax.set_yticks(range(len(units)))
ax.set_yticklabels([u.replace("repair_", "") for u in dedup_labels],
                   fontsize=6.5)
for i in range(len(units)):
    for j in range(3):
        v = M[i, j]
        if not math.isnan(v):
            ax.text(j, i, "PASS" if v == 1 else "FAIL", ha="center",
                    va="center", fontsize=5.6,
                    color="white" if v < 0.5 else "black")
ax.set_title("Locked units x intervention arm\n(green=rescued)", fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "fig2_rescue_matrix.pdf")
fig.savefig(FIG / "fig2_rescue_matrix.png", dpi=200)
with open(FIG / "fig2_rescue_matrix.csv", "w", newline="") as f:
    wcsv = csv.DictWriter(f, fieldnames=list(rows2[0].keys()))
    wcsv.writeheader()
    wcsv.writerows(rows2)

# ---------------- Fig 3: AST distance trajectories ----------------
ast_rows = list(csv.DictReader(
    open(ROOT / "analysis" / "figures_data" / "ast_structure_distance.csv")))
cases = {  # label -> (run, model, arm, task, seed)
    "rescued switch: 7B v4_08 diverse": ("E4v4", "7B", "repair_diverse", "v4_08", "0"),
    "rescued switch: 3B v4_08 diverse s2": ("E6lock", "3B", "repair_diverse", "v4_08", "2"),
    "tinkering (no switch): 7B v5_09 diverse s0": ("E5", "7B", "repair_diverse", "v5_09", "0"),
    "verbatim lock (no switch): 7B v4_01 structured": ("E4v4", "7B", "repair_structured", "v4_01", "0"),
    "switch w/o rescue: 3B v2_13 diverse s0": ("E6v2", "3B", "repair_diverse", "v2_13", "0"),
}
fig, ax = plt.subplots(figsize=(5.2, 3.2))
styles = ["-", "--", "-.", ":", "-"]
colors = ["#1a7e1f", "#4daf4a", "#e69f00", "#666666", "#d6604d"]
rows3 = []
for (label, (run, model, arm, task, seed)), ls, col in zip(
        cases.items(), styles, colors):
    sel = [r for r in ast_rows if r["run"] == run and r["arm"] == arm
           and r["task"] == task and str(r["seed"]) == seed]
    sel.sort(key=lambda r: int(r["coder_idx"]))
    xs = [int(r["coder_idx"]) for r in sel]
    ys = [float(r["dist_to_step1"]) for r in sel]
    ax.plot(xs, ys, marker="o", markersize=3.5, linestyle=ls, color=col,
            label=label)
    for r in sel:
        rows3.append({"series": label, "coder_idx": r["coder_idx"],
                      "dist_to_step1": r["dist_to_step1"],
                      "dist_to_prev": r["dist_to_prev"]})
ax.axhline(0.25, color="black", linewidth=0.7, linestyle=":")
ax.text(1.02, 0.257, "switch threshold $\\tau$=0.25", fontsize=6.5)
ax.set_xlabel("candidate iteration")
ax.set_ylabel("AST structure distance to candidate 1")
ax.set_ylim(-0.02, 0.9)
ax.legend(fontsize=6.5, frameon=False, loc="upper left")
ax.set_title("Structural distance trajectories: switching is necessary\n"
             "but not sufficient for rescue", fontsize=8.5)
fig.tight_layout()
fig.savefig(FIG / "fig3_ast_typology.pdf")
fig.savefig(FIG / "fig3_ast_typology.png", dpi=200)
with open(FIG / "fig3_ast_typology.csv", "w", newline="") as f:
    wcsv = csv.DictWriter(f, fieldnames=list(rows3[0].keys()))
    wcsv.writeheader()
    wcsv.writerows(rows3)

print("figures written:", sorted(p.name for p in FIG.iterdir()))
