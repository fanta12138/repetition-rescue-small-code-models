#!/usr/bin/env python3
"""Offline AST structural-distance analysis for lock-in typology (E6-era).

For every coder step of the known lock cases, extract the candidate code,
anonymize user-defined identifiers (keep control flow + algorithm vocabulary
like sorted/Counter/range), tokenize the AST dump, and compute normalized
Levenshtein distances between consecutive candidates and vs. step 1.

Frozen criterion (paper outline §5.5): normalized structure distance
>= SWITCH_TAU counts as a structural jump ("family switch"); below it,
"within-family tinkering / drift".

Outputs analysis/figures_data/ast_structure_distance.csv (per step)
and analysis/figures_data/ast_case_matrix.csv (per case).
"""
import ast
import csv
import json
import re
from pathlib import Path

ROOT = Path("/mnt/g/paper0816")
OUT = ROOT / "analysis" / "figures_data"
OUT.mkdir(parents=True, exist_ok=True)

SWITCH_TAU = 0.25  # frozen threshold for "family switch"

# (run_dir, dataset_label, model, arms, task_ids, seeds)
CASES = [
    ("E4v2lock", "7B", ["repair_structured", "repair_diverse", "repair_nudge_weak"], ["v2_11"], [0]),
    ("E4v4",     "7B", ["repair_structured", "repair_diverse", "repair_nudge_weak"], ["v4_01", "v4_08"], [0]),
    ("E4v3lock", "7B", ["repair_structured", "repair_diverse", "repair_nudge_weak"], ["v3_07"], [0]),
    ("E5",       "7B", ["repair_structured", "repair_diverse", "repair_nudge_weak"], ["v5_04", "v5_07", "v5_09"], [0, 1]),
    ("E6lock",   "3B", ["repair_structured", "repair_diverse", "repair_nudge_weak"], ["v4_08"], [0, 1, 2, 3, 4]),
    ("E6v2",     "3B", ["repair_structured", "repair_diverse"], ["v2_13", "v2_14", "v2_15"], [0, 1, 2, 3, 4]),
]

CODE_RE = re.compile(r"```python\s*\n(.*?)```", re.DOTALL)


def extract_code(excerpt: str) -> str | None:
    blocks = CODE_RE.findall(excerpt or "")
    if not blocks:
        return None
    return max(blocks, key=len)


class Anonymizer(ast.NodeTransformer):
    """Rename user-defined identifiers to positional tokens; keep builtins."""

    def __init__(self, local_names):
        self.map = {}
        for n in local_names:
            self.map[n] = f"V{len(self.map)}"

    def visit_Name(self, node):
        if node.id in self.map:
            node.id = self.map[node.id]
        return node

    def visit_arg(self, node):
        if node.arg in self.map:
            node.arg = self.map[node.arg]
        return node

    def visit_FunctionDef(self, node):
        node.name = "sol"
        self.generic_visit(node)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef


def collect_local_names(tree: ast.AST) -> set:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
            names.update(a.arg for a in node.args.args)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


def structure_tokens(code: str) -> list[str] | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    locals_ = collect_local_names(tree)
    tree = Anonymizer(locals_).visit(tree)
    dump = ast.dump(tree)
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+", dump)


def levenshtein(a: list, b: list) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def norm_dist(a: list, b: list) -> float:
    m = max(len(a), len(b))
    return levenshtein(a, b) / m if m else 0.0


def load_metrics(run: str, arm: str, seed: int) -> dict:
    p = ROOT / "runs" / run / f"seed{seed}" / arm / "metrics.jsonl"
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            out[r["instance_id"]] = r
    return out


rows, case_rows = [], []
for run, model, arms, tasks, seeds in CASES:
    for arm in arms:
        for seed in seeds:
            tpath = ROOT / "runs" / run / f"seed{seed}" / arm / "trajectories.jsonl"
            if not tpath.exists():
                continue
            metrics = load_metrics(run, arm, seed)
            steps = {}
            for line in tpath.read_text().splitlines():
                t = json.loads(line)
                if t["instance_id"] not in tasks or t.get("role") != "coder":
                    continue
                ex = (t.get("extra") or {}).get("response_excerpt", "")
                code = extract_code(ex)
                steps.setdefault(t["instance_id"], []).append(
                    (t["step"], structure_tokens(code) if code else None))
            for tid in tasks:
                seq = steps.get(tid, [])
                if not seq:
                    continue
                met = metrics.get(tid, {})
                toks = [s[1] for s in seq]
                base = toks[0]
                prev = None
                for i, (stp, tk) in enumerate(seq):
                    dp = norm_dist(prev, tk) if prev and tk else None
                    d1 = norm_dist(base, tk) if base and tk else None
                    rows.append({
                        "run": run, "model": model, "arm": arm, "task": tid,
                        "seed": seed, "step": stp, "coder_idx": i + 1,
                        "seq_len": len(tk) if tk else None,
                        "dist_to_prev": round(dp, 4) if dp is not None else None,
                        "dist_to_step1": round(d1, 4) if d1 is not None else None,
                    })
                    prev = tk
                valid = [t for t in toks if t]
                dists = [norm_dist(a, b) for a, b in zip(valid, valid[1:])]
                maxd = max(dists) if dists else None
                case_rows.append({
                    "run": run, "model": model, "arm": arm, "task": tid, "seed": seed,
                    "success": met.get("success"), "iterations": met.get("iterations"),
                    "repetition_events": met.get("repetition_events"),
                    "n_candidates": len(valid),
                    "max_consec_dist": round(maxd, 4) if maxd is not None else None,
                    "final_dist_to_step1": round(norm_dist(valid[0], valid[-1]), 4) if len(valid) > 1 else 0.0,
                    "structural_jump": (maxd is not None and maxd >= SWITCH_TAU),
                })

with open(OUT / "ast_structure_distance.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
with open(OUT / "ast_case_matrix.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(case_rows[0].keys()))
    w.writeheader()
    w.writerows(case_rows)

print(f"steps={len(rows)} cases={len(case_rows)} tau={SWITCH_TAU}")
hdr = ["model", "task", "arm", "seed", "succ", "rep", "maxd", "d_end", "jump"]
print("{:<4} {:<7} {:<20} {:>4} {:>4} {:>3} {:>6} {:>6} {:>4}".format(*hdr))
for c in sorted(case_rows, key=lambda x: (x["model"], x["task"], x["arm"], x["seed"])):
    print("{:<4} {:<7} {:<20} {:>4} {:>4} {:>3} {:>6} {:>6} {:>4}".format(
        c["model"], c["task"], c["arm"], c["seed"],
        int(bool(c["success"])),
        c["repetition_events"] if c["repetition_events"] is not None else -1,
        c["max_consec_dist"] if c["max_consec_dist"] is not None else -1,
        c["final_dist_to_step1"],
        int(c["structural_jump"])))
