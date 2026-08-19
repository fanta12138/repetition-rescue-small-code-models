"""Sanity test for E1 actionable feedback parsers against real pytest output."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

from agent.feedback import contrastive_feedback, parse_pytest_verbose, structured_feedback
from data.selfbuilt.tasks_v2 import TASKS
from tools.sandbox import run_pytest


def main() -> None:
    # Pick one task whose buggy code fails some but not all cases (v2_01).
    task = next(t for t in TASKS if t["task_id"] == "v2_01")
    with tempfile.TemporaryDirectory(prefix="fb_test_") as d:
        wd = Path(d)
        (wd / "solution.py").write_text(task["buggy_code"], encoding="utf-8")
        (wd / "test_solution.py").write_text(task["test_code"], encoding="utf-8")
        res = run_pytest(wd, timeout_sec=20, verbose=True)
        print(f"passed={res.passed} returncode={res.returncode}")
        print("----- raw (first 1500 chars) -----")
        print(res.output[:1500])
        passed_cases, failed_cases = parse_pytest_verbose(res.output)
        print("----- parsed -----")
        print("passed:", passed_cases)
        print("failed:", failed_cases)
        assert failed_cases, "parser found no failing cases!"
        print("----- structured feedback -----")
        print(structured_feedback(res.output))
        print("----- contrastive feedback -----")
        print(contrastive_feedback(res.output))

    # Timeout case (v2_03 buggy = infinite loop) must degrade gracefully.
    task3 = next(t for t in TASKS if t["task_id"] == "v2_03")
    with tempfile.TemporaryDirectory(prefix="fb_test3_") as d:
        wd = Path(d)
        (wd / "solution.py").write_text(task3["buggy_code"], encoding="utf-8")
        (wd / "test_solution.py").write_text(task3["test_code"], encoding="utf-8")
        res = run_pytest(wd, timeout_sec=10, verbose=True)
        print("----- timeout case structured (fallback expected) -----")
        print(structured_feedback(res.output, max_chars=400)[:400])


if __name__ == "__main__":
    main()
