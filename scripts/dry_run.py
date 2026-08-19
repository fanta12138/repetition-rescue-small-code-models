"""GPU-free dry run: verifies the full pipeline wiring with a FakeLLM.

FakeLLM behavior: attempt 1 returns the buggy code unchanged (simulating a
failed first try); attempt >= 2 returns the gold fix (simulating that
informative feedback eventually leads to a correct repair). Expected outcome:
    direct  -> 0% success (only gets the "failed first try")
    repair  -> 100% success in 2 iterations

Usage:
    python -m scripts.dry_run [--tasks 3]
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path

from agent.llm import LLMResponse
from agent.loop import RepairLoop
from agent.trajectory import TrajectoryLogger
from data.selfbuilt.tasks import TASKS

ATTEMPT_RE = re.compile(r"第 (\d+) 次尝试前")


class FakeLLM:
    """Returns buggy code on attempt 1, gold fix from attempt 2 onward."""

    def __init__(self, tasks_by_id: dict) -> None:
        self.tasks = tasks_by_id

    def generate(self, messages, **kwargs) -> LLMResponse:
        user = messages[-1]["content"]
        m = ATTEMPT_RE.search(user)
        attempt = int(m.group(1)) if m else 1
        # Identify task by matching its buggy code in the prompt.
        task = next(
            (t for t in self.tasks.values() if t["buggy_code"].strip() in user), None
        )
        assert task is not None, "FakeLLM could not identify the task in prompt"
        code = task["buggy_code"] if attempt == 1 else task["fixed_code"]
        text = f"```python\n{code}```"
        return LLMResponse(
            text=text,
            prompt_tokens=len(user) // 4,
            completion_tokens=len(text) // 4,
            wall_time=0.1,
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=int, default=3)
    args = ap.parse_args()

    tasks = TASKS[: args.tasks]
    tasks_by_id = {t["task_id"]: t for t in tasks}
    cfg = {
        "budget": {
            "max_iterations": 5,
            "max_tokens_per_instance": 50000,
            "feedback_max_chars": 6000,
        },
        "sandbox": {"backend": "subprocess", "timeout_sec": 30},
    }

    out_root = Path(tempfile.mkdtemp(prefix="dryrun_"))
    print(f"输出目录: {out_root}\n")
    for mode in ("direct", "repair"):
        mode_dir = out_root / mode
        mode_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        with TrajectoryLogger(mode_dir / "trajectories.jsonl") as logger:
            loop = RepairLoop(cfg, FakeLLM(tasks_by_id), logger)
            for task in tasks:
                row = loop.run(task, mode)
                rows.append(row)
                print(
                    f"[{mode}] {task['task_id']}: "
                    f"{'PASS' if row['success'] else 'FAIL'} iters={row['iterations']}"
                )
        with open(mode_dir / "metrics.jsonl", "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Validate expectations
    direct_ok = all(
        not r["success"]
        for r in json.loads(
            "[" + ",".join((out_root / "direct" / "metrics.jsonl").read_text(encoding="utf-8").splitlines()) + "]"
        )
    )
    repair_rows = [
        json.loads(ln)
        for ln in (out_root / "repair" / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    repair_ok = all(r["success"] and r["iterations"] == 2 for r in repair_rows)
    print()
    print(f"direct 全部失败(符合预期): {direct_ok}")
    print(f"repair 全部在第 2 轮修复成功(符合预期): {repair_ok}")
    if direct_ok and repair_ok:
        print("干跑通过: loop / 沙箱 / 轨迹 / 提取 全链路正常。")
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
