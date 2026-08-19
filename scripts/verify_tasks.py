"""Validate the self-built debug set BEFORE any model runs.

For every task:
    1. buggy_code / files        must FAIL the tests (otherwise not a bug);
    2. fixed_code / files_fixed  must PASS the tests (otherwise gold is wrong).

Usage:
    python -m scripts.verify_tasks [--set v1|v2|v3|v4|v5]
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from tools.sandbox import run_pytest


def check(code: str, test_code: str) -> tuple[bool, str]:
    workdir = Path(tempfile.mkdtemp(prefix="verify_"))
    (workdir / "solution.py").write_text(code, encoding="utf-8")
    (workdir / "test_solution.py").write_text(test_code, encoding="utf-8")
    result = run_pytest(workdir, timeout_sec=30)
    return result.passed, result.output


def check_files(files: dict, test_code: str) -> tuple[bool, str]:
    """v3 multi-file variant: write every project file, then run pytest."""
    workdir = Path(tempfile.mkdtemp(prefix="verify_v3_"))
    for name, content in files.items():
        (workdir / name).write_text(content, encoding="utf-8")
    (workdir / "test_solution.py").write_text(test_code, encoding="utf-8")
    result = run_pytest(workdir, timeout_sec=30)
    return result.passed, result.output


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["v1", "v2", "v3", "v4", "v5"], default="v1")
    args = ap.parse_args()
    if args.set == "v2":
        from data.selfbuilt.tasks_v2 import TASKS
    elif args.set == "v3":
        from data.selfbuilt.tasks_v3 import TASKS
    elif args.set == "v4":
        from data.selfbuilt.tasks_v4 import TASKS
    elif args.set == "v5":
        from data.selfbuilt.tasks_v5 import TASKS
    else:
        from data.selfbuilt.tasks import TASKS

    failures = []
    for task in TASKS:
        tid = task["task_id"]
        if "files" in task:
            buggy_pass, out_buggy = check_files(task["files"], task["test_code"])
            fixed_pass, out_fixed = check_files(task["files_fixed"], task["test_code"])
            if task["bug_file"] not in task["files"]:
                failures.append(f"{tid}: bug_file 不在 files 中")
        else:
            buggy_pass, out_buggy = check(task["buggy_code"], task["test_code"])
            fixed_pass, out_fixed = check(task["fixed_code"], task["test_code"])
        if buggy_pass:
            failures.append(f"{tid}: buggy 代码竟然通过了测试（题目无效）")
        if not fixed_pass:
            failures.append(f"{tid}: fixed 代码未通过测试（参考答案错误）\n{out_fixed[-500:]}")
        status = "OK" if not buggy_pass and fixed_pass else "FAIL"
        print(f"[{status}] {tid} ({task['bug_type']})")

    if failures:
        print("\n发现以下问题，必须修复后才能跑实验:")
        for f in failures:
            print(" -", f)
        return 1
    print(f"\n全部 {len(TASKS)} 题校验通过: buggy 均失败、fixed 均通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
