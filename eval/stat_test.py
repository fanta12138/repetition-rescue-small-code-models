"""Paired significance tests for multi-seed E0 runs.

Usage:
    python -m eval.stat_test --run runs/E0v2s5 \
        --pairs repair:no_feedback repair:random_reflection repair:direct

For each (seed, instance) pair we have a binary outcome under both arms,
so the correct test is McNemar's exact (binomial) test on the discordant
pairs, NOT an independent-proportions test.

  b = A pass & B fail     c = A fail & B pass
  p = 2 * P(X <= min(b,c)),  X ~ Binomial(b+c, 0.5)   (two-sided, clipped at 1)

Also reports the Newcombe-Wilson score interval for the paired difference
(p_A - p_B) as an effect-size complement.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def load_mode(base: Path, mode: str) -> dict[tuple[str, str], bool]:
    """Return {(seed_name, instance_id): success} for one arm."""
    out: dict[tuple[str, str], bool] = {}
    for seed_dir in sorted(base.iterdir()):
        mf = seed_dir / mode / "metrics.jsonl"
        if not (seed_dir.is_dir() and mf.exists()):
            continue
        for line in mf.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            out[(seed_dir.name, row["instance_id"])] = bool(row["success"])
    return out


def binom_cdf(k: int, n: int, p: float = 0.5) -> float:
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2.0 * binom_cdf(min(b, c), n))


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (center - half) / denom, (center + half) / denom


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument(
        "--pairs",
        nargs="+",
        default=["repair:no_feedback", "repair:random_reflection", "repair:direct"],
        help="armA:armB pairs to compare",
    )
    args = ap.parse_args()

    print(f"run = {args.run}")
    for spec in args.pairs:
        name_a, name_b = spec.split(":")
        res_a = load_mode(args.run, name_a)
        res_b = load_mode(args.run, name_b)
        keys = sorted(set(res_a) & set(res_b))
        if not keys:
            print(f"\n[{spec}] no paired instances found")
            continue

        b = c = 0
        for k in keys:
            if res_a[k] and not res_b[k]:
                b += 1
            elif res_b[k] and not res_a[k]:
                c += 1
        n = len(keys)
        pa = sum(res_a[k] for k in keys) / n
        pb = sum(res_b[k] for k in keys) / n
        p_val = mcnemar_exact(b, c)
        lo, hi = wilson_interval(b, b + c) if (b + c) else (0.0, 0.0)

        print(f"\n[{name_a} vs {name_b}]  n={n} paired instances")
        print(f"  success: {name_a}={pa:.1%}  {name_b}={pb:.1%}  diff={pa-pb:+.1%}")
        print(f"  discordant: {name_a} pass & {name_b} fail = {b}; "
              f"{name_a} fail & {name_b} pass = {c}")
        print(f"  McNemar exact two-sided p = {p_val:.4f}")
        sig = "SIGNIFICANT" if p_val < 0.05 else "not significant"
        print(f"  -> {sig} at alpha=0.05")
        if b + c:
            print(f"  Wilson CI for discordance ratio: [{lo:.3f}, {hi:.3f}]")


if __name__ == "__main__":
    main()
