"""E8: HumanEval lock-in prevalence & intervention transfer.

Preregistered 2026-08-18 (analysis/RESEARCH_LOG.md), frozen before any
E8 data was observed.

Protocol adaptation (generate-test-revise):
  - attempt 1 = one-shot function completion of the HumanEval prompt stub;
  - execution = solution.py (completion) + pytest-wrapped entry tests;
  - on failure: structured feedback, revise, up to T_max=5 attempts.
Arms: direct / repair_structured / repair_diverse / repair_nudge_weak,
5 seeds, temperature 0.2, budgets identical to E0.

Frozen format guard: if an extracted candidate lacks the function
signature (`def {entry_point}`), the HumanEval prompt is prepended
(same rule as scripts/smoke_humaneval.py), so format artifacts are
never counted as behavioral locks.

Usage:
    python -m scripts.run_e8_humaneval --config configs/e8.yaml \
        --seeds 0,1,2,3,4 [--limit N] [--task-ids HumanEval_0,...]
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

DESCRIPTION_TEMPLATE = (
    "请补全下面的 Python 函数（HumanEval 任务 {task_id}）。"
    "当前代码只包含函数签名与 docstring，请给出完整、可直接运行的实现。"
)


def load_humaneval_tasks(path: str = "data/humaneval.jsonl") -> list[dict]:
    entries = [json.loads(ln) for ln in
               Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    tasks = []
    for e in entries:
        ep = e["entry_point"]
        # Pytest wrapper: HumanEval tests are assert-based `check(candidate)`
        # functions; wrap the check call in a real test so run_pytest and the
        # structured-feedback parser behave identically to the self-built
        # suites (same oracle contract, same feedback pipeline).
        test_code = (
            f"from solution import {ep}\n\n"
            f"{e['test']}\n\n"
            f"def test_solution():\n"
            f"    check({ep})\n"
        )
        tasks.append({
            "task_id": e["task_id"].replace("/", "_"),
            "description": DESCRIPTION_TEMPLATE.format(task_id=e["task_id"]),
            "buggy_code": e["prompt"],          # signature + docstring stub
            "test_code": test_code,
            "he_prompt": e["prompt"],
            "he_entry_point": ep,
        })
    return tasks


class HumanEvalLoop(RepairLoop):
    """RepairLoop with the frozen HumanEval signature-prepend guard."""

    def _install_candidate(self, task: dict, new_code: str) -> str:
        ep = task.get("he_entry_point")
        if ep and f"def {ep}" not in new_code:
            # Model returned only the body (or a renamed function): prepend
            # the original signature block so execution and repetition
            # detection both see the actual installed program.
            return task["he_prompt"] + "\n" + new_code
        return new_code


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/e8.yaml")
    ap.add_argument("--modes", default=None)
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--task-ids", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    modes = args.modes.split(",") if args.modes else cfg["modes"]
    for m in modes:
        assert m in MODES, f"unknown mode {m}; valid: {MODES}"
    seeds = [int(s) for s in args.seeds.split(",")]

    tasks = load_humaneval_tasks(cfg.get("humaneval_path",
                                           "data/humaneval.jsonl"))
    tasks = tasks[: args.limit or len(tasks)]
    if args.task_ids:
        wanted = set(args.task_ids.split(","))
        tasks = [t for t in tasks if t["task_id"] in wanted]
        assert tasks, f"no tasks match --task-ids {args.task_ids}"

    llm_cfg = cfg["llm"]
    out_root = Path(args.out or cfg["output_dir"])
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "run_meta.json").write_text(json.dumps({
        "experiment": cfg["experiment"], "model": llm_cfg["model"],
        "dataset": "humaneval", "modes": modes, "seeds": seeds,
        "n_tasks": len(tasks), "budget": cfg["budget"],
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    for seed in seeds:
        llm = LLMClient(
            base_url=llm_cfg["base_url"], api_key=llm_cfg.get("api_key", "EMPTY"),
            model=llm_cfg["model"], temperature=llm_cfg.get("temperature", 0.2),
            max_tokens=llm_cfg.get("max_tokens", 4096), seed=seed,
        )
        seed_root = out_root / f"seed{seed}"
        seed_root.mkdir(parents=True, exist_ok=True)
        print(f"\n########## seed={seed} ##########")
        for mode in modes:
            mode_dir = seed_root / mode
            mode_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n===== mode={mode} | tasks={len(tasks)} =====")
            with TrajectoryLogger(mode_dir / "trajectories.jsonl") as logger:
                loop = HumanEvalLoop(cfg, llm, logger)
                rows = []
                for i, task in enumerate(tasks, 1):
                    row = loop.run(task, mode)
                    rows.append(row)
                    print(f"[{mode}] {i}/{len(tasks)} {task['task_id']}: "
                          f"{'PASS' if row['success'] else 'FAIL'} "
                          f"(iters={row['iterations']}, "
                          f"tokens={row['total_tokens']}, "
                          f"rep={row['repetition_events']})")
            with open(mode_dir / "metrics.jsonl", "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("\nE8 完成。")


if __name__ == "__main__":
    main()
