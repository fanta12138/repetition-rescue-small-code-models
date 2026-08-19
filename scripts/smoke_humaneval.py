"""HumanEval smoke test: sanity-check base code ability of the served model.

Goal (week 1, D1-D2): confirm the model's function-level code capability
before investing in the agent loop. Expect pass@1 > 50% for
Qwen2.5-Coder-7B-Instruct on HumanEval; otherwise switch model.

Usage:
    python -m scripts.smoke_humaneval --n 20
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import yaml

from agent.llm import LLMClient
from tools.patch_utils import extract_code_block
from tools.sandbox import run_script

USER_TEMPLATE = """Complete the following Python function. Return ONLY the full
completed function (signature included) in a single ```python code block.

```python
{prompt}
```"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/e0_pilot.yaml")
    ap.add_argument("--n", type=int, default=20)
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    llm_cfg = cfg["llm"]
    llm = LLMClient(
        base_url=llm_cfg["base_url"], api_key=llm_cfg.get("api_key", "EMPTY"),
        model=llm_cfg["model"], temperature=0.0, max_tokens=1024,
    )

    local = Path("data/humaneval.jsonl")
    if local.exists():
        # Offline-friendly path: JSONL vendored from ModelScope (HF Hub unreachable).
        ds = [json.loads(line) for line in local.read_text(encoding="utf-8").splitlines()]
    else:
        from datasets import load_dataset  # deferred heavy import

        ds = list(load_dataset("openai_humaneval", split="test"))
    n = min(args.n, len(ds))

    passed = 0
    for i in range(n):
        entry = ds[i]
        messages = [
            {"role": "user", "content": USER_TEMPLATE.format(prompt=entry["prompt"])}
        ]
        resp = llm.generate(messages)
        code = extract_code_block(resp.text)
        if code is None:
            code = entry["prompt"]  # format failure -> cannot complete
        # If the model only returned the body, prepend the signature.
        if f"def {entry['entry_point']}" not in code:
            code = entry["prompt"] + code
        full = code + "\n" + entry["test"] + f"\ncheck({entry['entry_point']})\n"

        workdir = Path(tempfile.mkdtemp(prefix="he_"))
        script = workdir / "run.py"
        script.write_text(full, encoding="utf-8")
        result = run_script(script, timeout_sec=15)
        ok = result.passed
        passed += int(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {i+1}/{n} {entry['entry_point']}")

    print(f"\npass@1 = {passed}/{n} = {passed / n:.1%}")
    if passed / n < 0.5:
        print("警告: pass@1 < 50%，模型基础代码能力不足，建议更换模型再继续。")


if __name__ == "__main__":
    main()
