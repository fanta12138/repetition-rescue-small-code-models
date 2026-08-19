"""Prompt templates for the repair loop.

Design notes for small models:
- One task per prompt; the model only needs to output ONE complete file.
  Whole-file output is more reliable than unified-diff generation for 3B-7B
  models (diff format is an ablation dimension for later SWE-bench runs).
- Explicit output format instruction ("一个 python 代码块") keeps extraction
  deterministic; combine with vLLM guided decoding if format failures persist.
"""
from __future__ import annotations

from typing import Optional

SYSTEM_PROMPT = (
    "你是一名资深软件工程师，擅长定位并修复 Python 代码中的 bug。"
    "你会仔细阅读任务描述与测试反馈，找出根因并给出最小、正确的修复。"
    "你只输出修复后的完整代码，不做无关解释。"
)

FIRST_ATTEMPT_NOTE = "（第一次尝试，尚无测试反馈。请根据任务描述与代码现状直接修复。）"


def build_repair_messages(
    description: str,
    current_code: str,
    feedback: Optional[str],
    attempt: int,
) -> list[dict]:
    """Build chat messages for one repair attempt."""
    feedback_block = feedback if feedback else FIRST_ATTEMPT_NOTE
    user = f"""## 任务描述
{description}

## 当前代码（solution.py）
```python
{current_code}
```

## 测试运行反馈（第 {attempt} 次尝试前）
{feedback_block}

请输出修复后的完整 solution.py 代码。要求：
1. 放在一个 ```python 代码块中；
2. 包含完整的函数/类定义，可直接保存运行；
3. 不要输出其他文件或解释。"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def build_direct_messages(description: str, buggy_code: str) -> list[dict]:
    """Single-shot baseline prompt (no iteration, no feedback)."""
    user = f"""## 任务描述
{description}

## 当前代码（solution.py）中包含一个 bug，请修复它。
```python
{buggy_code}
```

请输出修复后的完整 solution.py 代码。要求：
1. 放在一个 ```python 代码块中；
2. 包含完整的函数/类定义，可直接保存运行；
3. 不要输出其他文件或解释。"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _format_files(files: dict[str, str]) -> str:
    """Render a {filename: code} map as filename-annotated code blocks."""
    parts = []
    for name in sorted(files):
        parts.append(f"```python {name}\n{files[name].rstrip()}\n```")
    return "\n\n".join(parts)


def build_multifile_repair_messages(
    description: str,
    files: dict[str, str],
    feedback: Optional[str],
    attempt: int,
) -> list[dict]:
    """Repair prompt for v3 multi-file tasks.

    The model must localize the bug itself: it chooses WHICH files to
    rewrite. Output contract: one ```python <filename> block per modified
    file, full content. Localization accuracy is a scored metric.
    """
    feedback_block = feedback if feedback else FIRST_ATTEMPT_NOTE
    user = f"""## 任务描述
{description}

## 项目文件（其中恰好有一个文件包含一个 bug）
{_format_files(files)}

## 测试运行反馈（第 {attempt} 次尝试前）
{feedback_block}

请定位 bug 所在的文件并修复。要求：
1. 只输出你修改过的文件，每个文件一个代码块；
2. 代码块开头必须标注文件名，格式为 ```python 文件名.py（如 ```python core.py）；
3. 每个代码块包含该文件的完整内容；
4. 未修改的文件不要输出，也不要解释。"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
