"""Structured compression of test-execution feedback.

Small models have tight context budgets: dumping raw pytest output (which can
include huge tracebacks) wastes budget and degrades repair quality. This
module keeps only the high-signal parts: FAILED/ERROR test names, the short
summary section, and the tail of the output (last traceback).

This compression step is itself a research mechanism under study -- the
feedback budget is controlled by configs and should be ablated later.
"""
from __future__ import annotations

import re

NO_FEEDBACK_TEXT = "测试未通过。请重新检查代码并给出修正后的完整实现。"

# E3 lock-breaking nudge: prepended to feedback when the model's previous
# candidate was byte-identical to the one before it AND still failed.
# Only observable information is used (repetition + failure), no oracle leak.
DIVERSITY_NUDGE = (
    "重要提示：你上一轮输出的修复方案与前一轮完全相同，且测试仍然失败。"
    "重复同一方案无法修复此 bug。请彻底放弃当前思路，"
    "重新分析根因，给出一个与之前完全不同的修复方案。"
)

# E4 ablation control: WEAK nudge with the same "you repeated" observation
# but a generic "try again" directive (no demand to switch approach).
# diverse vs weak isolates "switch-approach instruction" from "extra retry
# with repetition awareness".
WEAK_NUDGE = (
    "提示：你上一轮输出的修复方案与前一轮完全相同，且测试仍然失败。"
    "请再仔细检查一遍，再试一次。"
)

# Control arm: plausible-sounding but non-diagnostic text. If `repair` only
# beats this arm, the gain cannot be attributed to "more attempts" alone.
RANDOM_FEEDBACKS = [
    "代码整体风格看起来不错，请继续保持，再试一次。",
    "注意保持变量命名的一致性，再试一次。",
    "今天也是适合写代码的一天，请再检查一遍。",
    "建议回顾一下任务描述，然后重新输出代码。",
]


def compress_test_output(output: str, max_chars: int = 6000) -> str:
    """Compress pytest output to fit the feedback budget.

    Keeps: (1) FAILED/ERROR lines, (2) the short-test-summary section,
    (3) the tail of the raw output (last traceback). Total <= max_chars.
    """
    if not output or not output.strip():
        return "(测试无输出)"
    lines = output.splitlines()

    failed_lines = [ln for ln in lines if ln.startswith(("FAILED", "ERROR"))]

    summary_start = None
    for i, ln in enumerate(lines):
        if "short test summary" in ln:
            summary_start = i
            break

    parts: list[str] = []
    if failed_lines:
        parts.append("失败/错误的测试:\n" + "\n".join(failed_lines[:20]))
    if summary_start is not None:
        parts.append("\n".join(lines[summary_start : summary_start + 30]))

    used = sum(len(p) for p in parts) + 2 * len(parts)
    tail_budget = max_chars - used - 64
    if tail_budget > 200:
        parts.append("输出末尾:\n" + output[-tail_budget:])

    text = "\n\n".join(parts)
    if len(text) > max_chars:
        text = text[: max_chars]
    return text


# ---------------------------------------------------------------------------
# E1: actionable feedback formats
#
# Both formats use the SAME oracle (pytest) and the same token budget as
# `repair`; only the presentation of the failure information changes:
#   structured   -- clean per-failing-case list: case name + assertion diff
#   contrastive  -- additionally lists PASSING cases, exposing the
#                   pass/fail boundary (hypothesis: helps boundary bugs).
# ---------------------------------------------------------------------------

# pytest -v line: "test_solution.py::test_odd PASSED"
_V_CASE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR)")
# short summary line: "FAILED test_solution.py::test_odd - assert 2 == 3"
_SUMMARY_FAIL = re.compile(r"^(?:FAILED|ERROR)\s+(\S+::\S+)\s*-\s*(.+)$")
# assertion detail line inside a --tb=short traceback: "E   assert 2 == 3"
_E_LINE = re.compile(r"^E\s+(.+)$")


def parse_pytest_verbose(output: str) -> tuple[list[str], list[tuple[str, str]]]:
    """Parse `pytest -v --tb=short` output.

    Returns (passed_cases, failed_cases) where each failed case is
    (case_name, detail) and detail is the assertion/message excerpt.
    """
    if not output or not output.strip():
        return [], []
    lines = output.splitlines()

    passed: list[str] = []
    failed_order: list[str] = []
    failed_detail: dict[str, str] = {}

    for ln in lines:
        m = _V_CASE.match(ln.strip())
        if m:
            case, status = m.group(1), m.group(2)
            if status == "PASSED":
                passed.append(case.split("::")[-1])
            else:
                failed_order.append(case.split("::")[-1])
            continue
        m = _SUMMARY_FAIL.match(ln.strip())
        if m:
            case = m.group(1).split("::")[-1]
            if case not in failed_detail:
                failed_detail[case] = m.group(2).strip()

    # Enrich with per-case E-lines from tracebacks (fallback when the
    # short-summary line carries no expression, e.g. collection errors).
    current_case = None
    for ln in lines:
        m = _V_CASE.match(ln.strip())
        if m and m.group(2) != "PASSED":
            current_case = m.group(1).split("::")[-1]
            continue
        m = _E_LINE.match(ln.strip())
        if m and current_case and current_case not in failed_detail:
            failed_detail[current_case] = m.group(1).strip()

    # Keep summary-line detail preferred (it is one line, already condensed).
    failed = [(c, failed_detail.get(c, "（无断言详情）")) for c in failed_order]
    return passed, failed


def structured_feedback(output: str, max_chars: int = 6000) -> str:
    """Actionable feedback: one clean line per failing case.

    Hypothesis: the current compressed output buries the assertion diff in
    traceback noise; a clean case-level list lowers the utilization cost.
    """
    passed, failed = parse_pytest_verbose(output)
    if not failed:
        # Parser could not recognize any case -> degrade gracefully.
        return compress_test_output(output, max_chars)
    lines = [f"共 {len(passed) + len(failed)} 个测试用例，{len(failed)} 个失败。"]
    lines.append("失败的用例（名称 - 断言差异）：")
    for i, (case, detail) in enumerate(failed, 1):
        lines.append(f"{i}. {case}: {detail}")
    text = "\n".join(lines)
    return text[:max_chars]


def contrastive_feedback(output: str, max_chars: int = 6000) -> str:
    """Actionable feedback: passing AND failing cases side by side.

    Hypothesis: passing cases delimit the bug's boundary (which inputs
    still work), which should specifically help boundary-condition bugs.
    """
    passed, failed = parse_pytest_verbose(output)
    if not failed:
        return compress_test_output(output, max_chars)
    lines = [f"共 {len(passed) + len(failed)} 个测试用例："]
    if passed:
        lines.append("仍通过的用例：" + ", ".join(passed[:20]))
    lines.append("失败的用例（名称 - 断言差异）：")
    for i, (case, detail) in enumerate(failed, 1):
        lines.append(f"{i}. {case}: {detail}")
    lines.append("请对比通过与失败的用例，找出行为分界在哪里，再修复。")
    text = "\n".join(lines)
    return text[:max_chars]
