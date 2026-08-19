"""E8 preregistered adjudication (analysis/RESEARCH_LOG.md, frozen 2026-08-18).

Endpoints (frozen):
  P1 lock-in prevalence on HumanEval = locked seed-instances (structured
     fail & rep>=2) / all seed-instances, Clopper-Pearson 95% CI; plus the
     unit-level prevalence deduplicated by trajectory hash (E4 lesson).
  P2 locked instances: diverse vs structured, exact McNemar, p<0.025 &
     Delta>=3pp; if <10 locked instances -> descriptive per-unit report.
  P3 locked instances: diverse vs weak, same rule as P2.
  S1 loop gain: structured vs direct, same threshold.
  S2 determinism audit (unconditional): cross-seed trajectory-hash identity
     rate among locked instances.
  Interim rule (compute protection): after seeds 0-1, if >=90% of failed
     structured trajectories are byte-identical across the two seeds,
     seeds 2-4 run only locked instances + matched controls.

Usage:  python -m scripts.analyze_e8 [--root runs/E8] [--seeds 0,1]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


# ---------- Clopper-Pearson via regularized incomplete beta ----------

def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta (Lentz)."""
    MAXIT, EPS, FPMIN = 200, 3e-12, 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    from math import exp, lgamma, log
    ln_front = (lgamma(a + b) - lgamma(a) - lgamma(b)
                + a * log(x) + b * log(1.0 - x))
    front = exp(ln_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _beta_quantile(p: float, a: float, b: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if _betainc(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else _beta_quantile(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else _beta_quantile(1 - alpha / 2, k + 1, n - k)
    return lo, hi


def exact_mcnemar(pairs: list[tuple[bool, bool]]) -> tuple[float, int, int]:
    b = sum(1 for a, bb in pairs if (not a) and bb)
    c = sum(1 for a, bb in pairs if a and (not bb))
    n = b + c
    if n == 0:
        return 1.0, b, c
    from math import comb
    k = min(b, c)
    p = sum(comb(n, i) for i in range(k + 1)) * 2 / (2 ** n)
    return min(p, 1.0), b, c


# ---------- loading ----------

def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


def traj_hash(mode_dir: Path, instance_id: str) -> str | None:
    """sha1 of concatenated coder response excerpts for one instance."""
    p = mode_dir / "trajectories.jsonl"
    if not p.exists():
        return None
    parts = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        r = json.loads(ln)
        if r["instance_id"] == instance_id and r["role"] == "coder":
            parts.append(r.get("extra", {}).get("response_excerpt", ""))
    if not parts:
        return None
    return hashlib.sha1("\n".join(parts).encode()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="runs/E8")
    ap.add_argument("--seeds", default="0,1,2,3,4")
    args = ap.parse_args()
    root = Path(args.root)
    seeds = [int(s) for s in args.seeds.split(",")]

    arms = {}
    for mode in ("direct", "repair_structured", "repair_diverse",
                 "repair_nudge_weak"):
        arms[mode] = {}
        for seed in seeds:
            p = root / f"seed{seed}" / mode / "metrics.jsonl"
            if p.exists():
                for r in load_jsonl(p):
                    arms[mode][(r["instance_id"], seed)] = r

    struct = arms["repair_structured"]
    if not struct:
        print("no structured data yet")
        return

    n_units = len(struct)
    locked = [(iid, s) for (iid, s), r in struct.items()
              if (not r["success"]) and r["repetition_events"] >= 2]
    k = len(locked)
    lo, hi = clopper_pearson(k, n_units)

    print(f"\n================ E8 HumanEval ================")
    for mode in ("direct", "repair_structured", "repair_diverse",
                 "repair_nudge_weak"):
        rows = arms[mode]
        if rows:
            s = sum(r["success"] for r in rows.values())
            print(f"  {mode:20s} pass {s}/{len(rows)} = {100*s/len(rows):.1f}%")

    print(f"\n-- P1 lock-in prevalence (frozen criterion: struct fail & "
          f"rep>=2) --")
    print(f"  seed-instance level: {k}/{n_units} = {100*k/n_units:.2f}%  "
          f"Clopper-Pearson 95% CI [{100*lo:.2f}%, {100*hi:.2f}%]")

    # unit-level dedup by trajectory hash
    hashes = {}
    for iid, s in locked:
        d = root / f"seed{s}" / "repair_structured"
        hashes[(iid, s)] = traj_hash(d, iid)
    uniq = {h for h in hashes.values() if h}
    tasks_locked = sorted({iid for iid, _ in locked})
    print(f"  locked tasks: {tasks_locked}")
    print(f"  distinct trajectory hashes among locked units: "
          f"{len(uniq)}/{len([h for h in hashes.values() if h])}")

    # S2 determinism audit: same task locked on >=2 seeds -> hash identity
    from collections import defaultdict
    by_task = defaultdict(list)
    for iid, s in locked:
        by_task[iid].append((s, hashes.get((iid, s))))
    ident = tot = 0
    for iid, lst in sorted(by_task.items()):
        if len(lst) >= 2 and all(h for _, h in lst):
            hs = [h for _, h in lst]
            tot += 1
            if len(set(hs)) == 1:
                ident += 1
            print(f"  S2 {iid}: seeds={[s for s, _ in lst]} "
                  f"identical={len(set(hs)) == 1}")
    if tot:
        print(f"  S2 cross-seed identity rate (tasks locked >=2 seeds): "
              f"{ident}/{tot}")

    # interim rule (seeds 0-1 only)
    failed01 = [(iid, s) for (iid, s), r in struct.items()
                if s in (0, 1) and not r["success"]]
    if failed01:
        fh = {}
        for iid, s in failed01:
            d = root / f"seed{s}" / "repair_structured"
            fh[(iid, s)] = traj_hash(d, iid)
        by_t = defaultdict(dict)
        for (iid, s), h in fh.items():
            by_t[iid][s] = h
        both = [t for t, d_ in by_t.items()
                if 0 in d_ and 1 in d_ and d_[0] and d_[1]]
        if both:
            same = sum(1 for t in both if by_t[t][0] == by_t[t][1])
            rate = same / len(both)
            verdict = ("TRIGGER: seeds 2-4 run locked instances + matched "
                       "controls only" if rate >= 0.9
                       else "NO TRIGGER: seeds 2-4 run full battery")
            print(f"\n-- interim rule: failed-struct tasks present in both "
                  f"seeds 0&1: {len(both)}, byte-identical {same} "
                  f"({100*rate:.0f}%) -> {verdict}")

    # P2 / P3 / S1
    def cmp(name: str, arm_a: dict, arm_b: dict, keys=None):
        ks = keys if keys is not None else sorted(set(arm_a) & set(arm_b))
        if not ks:
            print(f"  {name}: no overlapping units")
            return
        pairs = [(arm_a[k]["success"], arm_b[k]["success"]) for k in ks]
        pa = sum(arm_a[k]["success"] for k in ks) / len(ks)
        pb = sum(arm_b[k]["success"] for k in ks) / len(ks)
        p, b, c = exact_mcnemar(pairs)
        delta = 100 * (pb - pa)
        verdict = ("SIGNAL" if p < 0.025 and abs(delta) >= 3
                   else "null by frozen threshold")
        print(f"  {name}: {100*pa:.1f}% vs {100*pb:.1f}% "
              f"(Delta={delta:+.1f}pp, b={b}/c={c}, exact p={p:.4f}, "
              f"n={len(ks)}) -> {verdict}")

    print(f"\n-- P2/P3 on locked instances (frozen: p<0.025 & Delta>=3pp; "
          f"<10 units -> descriptive) --")
    if len(locked) < 10:
        print(f"  only {len(locked)} locked units -> descriptive per-unit "
              f"report (frozen fallback):")
        print(f"  {'unit':22s} struct diverse weak")
        for iid, s in sorted(locked):
            d = arms["repair_diverse"].get((iid, s))
            w = arms["repair_nudge_weak"].get((iid, s))
            fmt = lambda r: ("PASS" if r["success"] else "FAIL") if r else "-"
            print(f"  {iid}@s{s:<16d} FAIL   {fmt(d):7s} {fmt(w)}")
    else:
        cmp("P2 diverse vs structured (locked)", struct,
            arms["repair_diverse"], locked)
        cmp("P3 diverse vs weak (locked)", arms["repair_nudge_weak"],
            arms["repair_diverse"], locked)

    print(f"\n-- S1 loop gain: structured vs direct (full set) --")
    cmp("S1", arms["direct"], struct)


if __name__ == "__main__":
    main()
