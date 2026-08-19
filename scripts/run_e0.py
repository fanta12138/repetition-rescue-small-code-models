"""E0 pilot experiment runner.

Runs the self-built debug set under all configured arms:
    direct / repair / random_reflection / no_feedback

Outputs per arm under runs/E0/<mode>/:
    trajectories.jsonl  -- full step-level log (see agent/trajectory.py)
    metrics.jsonl       -- one row per instance (success, iterations, tokens...)

Usage:
    python -m scripts.run_e0 --config configs/e0_pilot.yaml [--modes repair,direct]
                             [--dataset v1|v2] [--out runs/E0v2]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml

from agent.llm import LLMClient
from agent.loop import MODES, RepairLoop
from agent.trajectory import TrajectoryLogger


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/e0_pilot.yaml")
    ap.add_argument("--modes", default=None, help="comma-separated subset of modes")
    ap.add_argument("--dataset", choices=["v1", "v2", "v3", "v4", "v5"], default="v1")
    ap.add_argument("--out", default=None, help="override output dir from config")
    ap.add_argument("--seeds", default=None, help="comma-separated seeds for replication")
    ap.add_argument("--limit", type=int, default=None, help="limit number of tasks")
    ap.add_argument("--task-ids", default=None,
                    help="comma-separated task_id subset (e.g. v2_11,v3_07)")
    args = ap.parse_args()

    if args.dataset == "v2":
        from data.selfbuilt.tasks_v2 import TASKS
    elif args.dataset == "v3":
        from data.selfbuilt.tasks_v3 import TASKS
    elif args.dataset == "v4":
        from data.selfbuilt.tasks_v4 import TASKS
    elif args.dataset == "v5":
        from data.selfbuilt.tasks_v5 import TASKS
    else:
        from data.selfbuilt.tasks import TASKS

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    modes = args.modes.split(",") if args.modes else cfg["modes"]
    for m in modes:
        assert m in MODES, f"unknown mode {m}; valid: {MODES}"
    tasks = TASKS[: args.limit or cfg["tasks"].get("selfbuilt_limit", len(TASKS))]
    if args.task_ids:
        wanted = set(args.task_ids.split(","))
        tasks = [t for t in tasks if t["task_id"] in wanted]
        assert tasks, f"no tasks match --task-ids {args.task_ids}"

    llm_cfg = cfg["llm"]
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [None]

    out_root = Path(args.out or cfg["output_dir"])
    run_meta = {
        "experiment": cfg["experiment"],
        "model": llm_cfg["model"],
        "dataset": args.dataset,
        "modes": modes,
        "seeds": seeds,
        "n_tasks": len(tasks),
        "budget": cfg["budget"],
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "run_meta.json").write_text(
        json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    for seed in seeds:
        llm = LLMClient(
            base_url=llm_cfg["base_url"],
            api_key=llm_cfg.get("api_key", "EMPTY"),
            model=llm_cfg["model"],
            temperature=llm_cfg.get("temperature", 0.2),
            max_tokens=llm_cfg.get("max_tokens", 4096),
            seed=seed,
        )
        seed_root = out_root if seed is None else out_root / f"seed{seed}"
        seed_root.mkdir(parents=True, exist_ok=True)
        if seed is not None:
            print(f"\n########## seed={seed} ##########")

        for mode in modes:
            mode_dir = seed_root / mode
            mode_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n===== mode={mode} | tasks={len(tasks)} =====")
            with TrajectoryLogger(mode_dir / "trajectories.jsonl") as logger:
                loop = RepairLoop(cfg, llm, logger)
                rows = []
                for i, task in enumerate(tasks, 1):
                    row = loop.run(task, mode)
                    rows.append(row)
                    print(
                        f"[{mode}] {i}/{len(tasks)} {task['task_id']}: "
                        f"{'PASS' if row['success'] else 'FAIL'} "
                        f"(iters={row['iterations']}, tokens={row['total_tokens']}, "
                        f"{row['wall_time']:.1f}s)"
                    )
            with open(mode_dir / "metrics.jsonl", "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\n完成。运行 `python -m eval.metrics --run {out_root}` 查看汇总指标。")


if __name__ == "__main__":
    main()
