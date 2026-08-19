"""SWE-bench integration adapter (week 1-2: pilot subset; week 3+: full runs).

The official swebench harness handles environment building, patch application
and test execution inside isolated containers. We do NOT reimplement that
here; this module is the thin interface between our agent loop and the
harness:

    1. load_subset()   -- read the pilot subset produced by
                          data/filter_pilot_subset.py
    2. prepare_input() -- build the agent prompt context (problem statement +
                          selected repo files via tools.repo_context)
    3. write_predictions() -- dump model patches in the swebench prediction
                          format (instance_id -> model_patch)
    4. Evaluation is then run OUTSIDE this repo with the official harness:

       python -m swebench.harness.run_evaluation \
           --dataset_name princeton-nlp/SWE-bench_Lite \
           --split dev \
           --predictions_path preds.json \
           --max_workers 4 --run_id E0_repair

Checklist before first SWE-bench run (week 1, D3-D4):
    [ ] pip install swebench; docker available; one dev instance runs end-to-end
    [ ] measure per-instance env-build time & disk (images are large)
    [ ] confirm FAIL_TO_PASS tests run within sandbox timeout
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def load_subset(path: str | Path) -> list[dict]:
    """Load pilot subset jsonl written by data/filter_pilot_subset.py."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"{p} 不存在。先运行: python -m data.filter_pilot_subset"
        )
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def prepare_input(instance: dict, repo_context: Optional[str] = None) -> dict:
    """Build the agent-facing input for one SWE-bench instance.

    repo_context is a budget-controlled concatenation of relevant files
    (week 3: produced by the retriever; week 1-2: the single changed file's
    neighborhood plus grep hits).
    """
    return {
        "instance_id": instance["instance_id"],
        "problem_statement": instance["problem_statement"],
        "repo": instance["repo"],
        "base_commit": instance["base_commit"],
        "repo_context": repo_context or "",
    }


def write_predictions(results: dict, path: str | Path) -> None:
    """Dump {instance_id: model_patch} in the format swebench expects."""
    Path(path).write_text(json.dumps(results, indent=2), encoding="utf-8")
