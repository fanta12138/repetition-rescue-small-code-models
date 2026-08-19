"""Per-task outcome matrix for an E0 run: which tasks each mode solved.

For flat runs (runs/E0v2) or pooled seed runs (runs/E0v2s). Highlights:
- RECOVERED: direct failed, loop mode succeeded -> candidate mechanism gain
- NOISE: direct failed but a loop mode passed at iters=1 -> sampling variance
- HARD: all modes failed -> failure-taxonomy candidates
"""
import json
import sys
from pathlib import Path

run = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/E0v2")


def mode_dirs(base: Path):
    for d in sorted(base.iterdir()):
        mf = d / "metrics.jsonl"
        if d.is_dir() and mf.exists():
            yield d.name, mf


# pooled: mode -> task_id -> list[(success, iterations)] (one entry per seed)
table: dict[str, dict[str, list[tuple[bool, int]]]] = {}


def ingest(prefix: str, base: Path) -> None:
    for mode, mf in mode_dirs(base):
        for ln in mf.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            r = json.loads(ln)
            table.setdefault(mode, {}).setdefault(r["instance_id"], []).append(
                (bool(r["success"]), r["iterations"])
            )


ingest("", run)
if not table:
    for sd in sorted(run.iterdir()):
        if sd.is_dir() and sd.name.startswith("seed"):
            ingest(sd.name, sd)

tasks = sorted(next(iter(table.values())).keys())
preferred = ["direct", "repair", "random_reflection", "no_feedback",
             "repair_structured", "repair_contrast",
             "repair_diverse", "repair_tempbump"]
modes = [m for m in preferred if m in table] + sorted(set(table) - set(preferred))

print("task | " + " | ".join(modes))
for t in tasks:
    cells = []
    for m in modes:
        outcomes = table[m].get(t, [(False, 0)])
        k = sum(ok for ok, _ in outcomes)
        cells.append(f"{k}/{len(outcomes)}" if len(outcomes) > 1 else ("PASS" if k else f"FAIL({outcomes[0][1]})"))
    print(f"{t} | " + " | ".join(cells))

print("\n--- 归因 ---")
if "direct" not in table:
    print("（本 run 无 direct 臂，跳过归因）")
for t in tasks:
    if "direct" not in table:
        break
    d_out = table["direct"].get(t, [(False, 0)])
    d_rate = sum(ok for ok, _ in d_out) / len(d_out)
    if d_rate >= 1.0:
        continue
    verdicts = []
    for m in modes[1:]:
        outcomes = table[m].get(t, [(False, 0)])
        rate = sum(ok for ok, _ in outcomes) / len(outcomes)
        iters = [it for ok, it in outcomes if ok]
        if rate > d_rate and iters and min(iters) == 1 and len(outcomes) == 1:
            verdicts.append(f"{m} 一次过→疑似采样噪声")
        elif rate > d_rate:
            verdicts.append(f"{m} {rate:.0%}>direct {d_rate:.0%} → 机制增益候选")
        elif rate == d_rate == 0.0:
            verdicts.append(f"{m} 也全挂")
    if all(v.endswith("也全挂") for v in verdicts):
        print(f"{t}: 全组失败 -> HARD，进入 failure taxonomy")
    else:
        print(f"{t} (direct {d_rate:.0%}): " + "; ".join(v for v in verdicts if not v.endswith("也全挂")))
