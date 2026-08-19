"""Aggregate E0 results: success rate, iterations, token cost, wall time.

Reads runs/E0/<mode>/metrics.jsonl for every mode present, prints a
comparison table and writes runs/E0/summary.json. Also reports the lift of
`repair` over `direct` -- the headline number of the pilot.

Usage:
    python -m eval.metrics --run runs/E0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean


def load_rows(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {}
    successes = sum(r["success"] for r in rows)
    llm_calls = [r["llm_calls"] for r in rows]
    tokens = [r["total_tokens"] for r in rows]
    times = [r["wall_time"] for r in rows]
    applied = sum(r["patch_applied_count"] for r in rows)
    attempts = sum(r["llm_calls"] for r in rows)
    out = {
        "n": n,
        "success_rate": successes / n,
        "successes": successes,
        "avg_iterations": mean(llm_calls),
        "avg_tokens": mean(tokens),
        "total_tokens": sum(tokens),
        "avg_wall_time_sec": mean(times),
        "patch_apply_rate": applied / attempts if attempts else 0.0,
        "extract_failures": sum(r["extract_failures"] for r in rows),
        "budget_exceeded": sum(r.get("error_type") == "budget_exceeded" for r in rows),
    }
    # v3 multi-file localization metrics (present only for multi-file tasks)
    if any("localized_bug_file" in r for r in rows):
        loc_rows = [r for r in rows if "localized_bug_file" in r]
        out["localization_rate"] = mean(r["localized_bug_file"] for r in loc_rows)
        out["avg_files_changed"] = mean(r["n_files_changed"] for r in loc_rows)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="runs/E0")
    args = ap.parse_args()

    run_dir = Path(args.run)

    # Collect rows per mode; supports both flat layout (<run>/<mode>/metrics.jsonl)
    # and replicated layout (<run>/seed<S>/<mode>/metrics.jsonl), pooling seeds.
    rows_by_mode: dict[str, list[dict]] = {}

    def collect(base: Path) -> None:
        for mode_dir in sorted(base.iterdir()):
            mf = mode_dir / "metrics.jsonl"
            if mode_dir.is_dir() and mf.exists():
                rows_by_mode.setdefault(mode_dir.name, []).extend(load_rows(mf))

    collect(run_dir)
    seed_dirs = []
    if not rows_by_mode:
        for seed_dir in sorted(run_dir.iterdir()):
            if seed_dir.is_dir() and seed_dir.name.startswith("seed"):
                collect(seed_dir)
                seed_dirs.append(seed_dir)

    summaries = {m: summarize(rows) for m, rows in rows_by_mode.items()}

    if not summaries:
        print(f"{run_dir} 下没有 metrics.jsonl，请先运行 scripts.run_e0")
        return

    # Markdown table
    cols = [
        ("mode", lambda s, m: m),
        ("success", lambda s, m: f"{s['successes']}/{s['n']} ({s['success_rate']:.0%})"),
        ("avg iters", lambda s, m: f"{s['avg_iterations']:.2f}"),
        ("avg tokens", lambda s, m: f"{s['avg_tokens']:.0f}"),
        ("total tokens", lambda s, m: f"{s['total_tokens']}"),
        ("avg time(s)", lambda s, m: f"{s['avg_wall_time_sec']:.1f}"),
        ("apply rate", lambda s, m: f"{s['patch_apply_rate']:.0%}"),
    ]
    header = " | ".join(c[0] for c in cols)
    print(header)
    print(" | ".join("---" for _ in cols))
    for mode, s in summaries.items():
        print(" | ".join(fn(s, mode) for _, fn in cols))

    # v3 localization table (only when multi-file rows are present)
    if any("localization_rate" in s for s in summaries.values()):
        print("\n定位指标 (v3 多文件):")
        print("mode | localization rate | avg files changed")
        print("--- | --- | ---")
        for mode, s in summaries.items():
            if "localization_rate" in s:
                print(
                    f"{mode} | {s['localization_rate']:.0%} | "
                    f"{s['avg_files_changed']:.2f}"
                )

    # Per-seed success rates (replicated runs): exposes sampling variance.
    if seed_dirs:
        print("\nper-seed success (方差检查):")
        for seed_dir in seed_dirs:
            parts = []
            for mode_dir in sorted(seed_dir.iterdir()):
                mf = mode_dir / "metrics.jsonl"
                if mode_dir.is_dir() and mf.exists():
                    s = summarize(load_rows(mf))
                    parts.append(f"{mode_dir.name}={s['success_rate']:.0%}")
            print(f"  {seed_dir.name}: " + "  ".join(parts))

    # Headline lift: repair vs direct
    if "repair" in summaries and "direct" in summaries:
        r, d = summaries["repair"]["success_rate"], summaries["direct"]["success_rate"]
        if d > 0:
            lift = (r - d) / d
            print(f"\nrepair vs direct: {r:.0%} vs {d:.0%} -> 相对提升 {lift:+.0%}")
            if lift < 0.30:
                print("提示: 未达到 +30% 相对提升的预警线，考虑转向反馈压缩/检索方向。")
        else:
            print(f"\nrepair vs direct: {r:.0%} vs {d:.0%} (direct 为 0，无法计算相对提升)")

    out = run_dir / "summary.json"
    out.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入 {out}")


if __name__ == "__main__":
    main()
