"""E7 preregistered adjudication (analysis/RESEARCH_LOG.md, frozen 2026-08-18).

Endpoints (frozen):
  P1 locked units (v4): diverse loop vs bestofn_seed / bestofn_temp rescue,
     per-unit deterministic report (no frequency claims). Locked set is the
     FROZEN E4v4 screen (structured fail & rep>=2), not re-derived here.
  P2 v2 full set: structured vs each best-of-N regime, exact McNemar,
     frozen threshold p<0.025 AND Delta>=3pp.
  S1 fairness: per-instance token ratio (best-of-N spend / matched budget),
     mean + quantiles.
  Diversity audit (unconditional): mean unique_ratio per regime.

Usage:  python -m scripts.analyze_e7 [--root runs/E7]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Frozen E4v4 locked seed-instances (structured arm, rep>=2); source:
# runs/E4v4/seed*/repair_structured/metrics.jsonl, frozen screening result.
E4V4_LOCKED = {
    ("v4_01", 0), ("v4_01", 1), ("v4_01", 2), ("v4_01", 3), ("v4_01", 4),
    ("v4_04", 1), ("v4_04", 4),
    ("v4_05", 0), ("v4_05", 4),
    ("v4_08", 0), ("v4_08", 1), ("v4_08", 2), ("v4_08", 3), ("v4_08", 4),
}


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


def load_loop(root: Path, dataset: str, mode: str) -> dict:
    """(iid, seed) -> metric row."""
    out = {}
    for seed_dir in sorted(root.glob("seed*")):
        seed = int(seed_dir.name[4:])
        p = seed_dir / mode / "metrics.jsonl"
        if not p.exists():
            continue
        for r in load_jsonl(p):
            out[(r["instance_id"], seed)] = r
    return out


def load_bestofn(root: Path, regime: str) -> dict:
    out = {}
    for seed_dir in sorted(root.glob("seed*")):
        seed = int(seed_dir.name[4:])
        p = seed_dir / regime / "metrics.jsonl"
        if not p.exists():
            continue
        for r in load_jsonl(p):
            out[(r["instance_id"], seed)] = r
    return out


def exact_mcnemar(pairs: list[tuple[bool, bool]]) -> tuple[float, int, int]:
    """pairs: (arm_a_success, arm_b_success). Returns (two-sided exact p,
    b, c) with b = a-fail&b-pass, c = a-pass&b-fail."""
    b = sum(1 for a, bb in pairs if (not a) and bb)
    c = sum(1 for a, bb in pairs if a and (not bb))
    n = b + c
    if n == 0:
        return 1.0, b, c
    from math import comb
    k = min(b, c)
    p = sum(comb(n, i) for i in range(k + 1)) * 2 / (2 ** n)
    return min(p, 1.0), b, c


def report_dataset(root: Path, dataset: str) -> None:
    ds_root = root / dataset
    if not ds_root.exists():
        print(f"[skip] {dataset}: no data yet")
        return
    structured = load_loop(ds_root, dataset, "repair_structured")
    diverse = load_loop(ds_root, dataset, "repair_diverse")
    weak = load_loop(ds_root, dataset, "repair_nudge_weak")
    bon_seed = load_bestofn(ds_root, "bestofn_seed")
    bon_temp = load_bestofn(ds_root, "bestofn_temp")

    print(f"\n================ E7 / {dataset} ================")
    for name, rows in [("structured", structured), ("diverse", diverse),
                       ("weak", weak), ("bestofn_seed", bon_seed),
                       ("bestofn_temp", bon_temp)]:
        if rows:
            n = len(rows)
            s = sum(r["success"] for r in rows.values())
            print(f"  {name:15s} pass {s}/{n} = {100*s/n:.1f}%")

    # ---- P1: locked-unit rescue table (v4 only) ----
    if dataset == "v4":
        print("\n-- P1 frozen locked units (E4v4 screen) --")
        print(f"{'unit':14s} {'diverse':8s} {'weak':8s} {'bon_seed':9s} "
              f"{'bon_temp':9s}")
        d_rescue_bon_fail = {"seed": 0, "temp": 0}
        for iid, seed in sorted(E4V4_LOCKED):
            d = diverse.get((iid, seed))
            w = weak.get((iid, seed))
            bs = bon_seed.get((iid, seed))
            bt = bon_temp.get((iid, seed))
            fmt = lambda r: ("PASS" if r["success"] else "FAIL") if r else "-"
            print(f"{iid}@s{seed:<8d} {fmt(d):8s} {fmt(w):8s} "
                  f"{fmt(bs):9s} {fmt(bt):9s}")
            if d and d["success"]:
                if bs and not bs["success"]:
                    d_rescue_bon_fail["seed"] += 1
                if bt and not bt["success"]:
                    d_rescue_bon_fail["temp"] += 1
        print(f"  diverse-rescued but bestofn_seed failed: "
              f"{d_rescue_bon_fail['seed']}")
        print(f"  diverse-rescued but bestofn_temp failed: "
              f"{d_rescue_bon_fail['temp']}")

    # ---- P2: v2 full set, structured vs best-of-N (exact McNemar) ----
    if dataset == "v2" and structured and bon_seed:
        keys = sorted(set(structured) & set(bon_seed))
        print("\n-- P2 v2 full set, exact McNemar (frozen: p<0.025 & "
              "Delta>=3pp) --")
        for regime, bon in [("bestofn_seed", bon_seed),
                            ("bestofn_temp", bon_temp)]:
            keys_r = sorted(set(structured) & set(bon))
            pairs = [(structured[k]["success"], bon[k]["success"])
                     for k in keys_r]
            pa = sum(structured[k]["success"] for k in keys_r) / len(keys_r)
            pb = sum(bon[k]["success"] for k in keys_r) / len(keys_r)
            p, b, c = exact_mcnemar(pairs)
            delta = 100 * (pb - pa)
            verdict = ("SIGNAL" if p < 0.025 and abs(delta) >= 3
                       else "null by frozen threshold")
            print(f"  structured vs {regime}: {100*pa:.1f}% vs {100*pb:.1f}% "
                  f"(Delta={delta:+.1f}pp, discordant b={b}/c={c}, "
                  f"exact p={p:.4f}) -> {verdict}")

    # ---- S1 fairness: token ratio ----
    for regime, bon in [("bestofn_seed", bon_seed), ("bestofn_temp", bon_temp)]:
        if not bon:
            continue
        ratios = sorted(r["tokens_used"] / r["budget_tokens"]
                        for r in bon.values())
        n = len(ratios)
        q = lambda f: ratios[min(n - 1, int(f * n))]
        print(f"\n-- S1 token ratio ({regime}, bon/matched budget): "
              f"mean={sum(ratios)/n:.2f} p50={q(.5):.2f} p90={q(.9):.2f} "
              f"max={ratios[-1]:.2f}")

    # ---- diversity audit (unconditional) ----
    for regime, bon in [("bestofn_seed", bon_seed), ("bestofn_temp", bon_temp)]:
        if not bon:
            continue
        ur = [r["unique_ratio"] for r in bon.values()]
        print(f"-- diversity audit {regime}: mean unique_ratio="
              f"{sum(ur)/len(ur):.3f} "
              f"(n={len(ur)}, fully-unique instances="
              f"{sum(1 for r in ur if r >= 0.999)})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="runs/E7")
    args = ap.parse_args()
    root = Path(args.root)
    for dataset in ("v2", "v4"):
        report_dataset(root, dataset)


if __name__ == "__main__":
    main()
