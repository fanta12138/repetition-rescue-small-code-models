"""Filter a pilot subset from SWE-bench (Lite) for E0.

Criteria (controlled subset, documented in the paper):
    - the gold patch touches EXACTLY ONE non-test file (single-file fix);
    - the gold patch file is a Python file;
    - FAIL_TO_PASS tests are present.

Note: SWE-bench_Lite's dev split has ~23 instances; if the filtered subset is
smaller than needed, point --dataset at the full SWE-bench dev split:
    --dataset princeton-nlp/SWE-bench --split dev

Usage:
    python -m data.filter_pilot_subset --out data/swe_pilot_subset.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DIFF_FILE_RE = re.compile(r"^diff --git a/(.+?) b/", re.M)


def changed_files(patch: str) -> list[str]:
    """List files touched by a git-style patch, in order, deduplicated."""
    return list(dict.fromkeys(DIFF_FILE_RE.findall(patch or "")))


def is_test_path(path: str) -> bool:
    parts = path.lower().split("/")
    name = parts[-1]
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or "tests" in parts
        or "test" in parts
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="princeton-nlp/SWE-bench_Lite")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--out", default="data/swe_pilot_subset.jsonl")
    ap.add_argument("--max-instances", type=int, default=30)
    args = ap.parse_args()

    from datasets import load_dataset  # deferred: heavy import

    ds = load_dataset(args.dataset, split=args.split)
    kept = []
    for inst in ds:
        files = changed_files(inst.get("patch", ""))
        if len(files) != 1:
            continue
        f = files[0]
        if is_test_path(f) or not f.endswith(".py"):
            continue
        if not inst.get("FAIL_TO_PASS"):
            continue
        kept.append(
            {
                "instance_id": inst["instance_id"],
                "repo": inst["repo"],
                "base_commit": inst["base_commit"],
                "problem_statement": inst["problem_statement"],
                "changed_file": f,
                "fail_to_pass": inst["FAIL_TO_PASS"],
                "pass_to_pass": inst.get("PASS_TO_PASS", []),
            }
        )
        if len(kept) >= args.max_instances:
            break

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        for item in kept:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"kept {len(kept)} instances (scanned {len(ds)}) -> {out}")
    if len(kept) < 10:
        print(
            "警告: 子集过小。可改用完整 SWE-bench dev split: "
            "--dataset princeton-nlp/SWE-bench --split dev"
        )


if __name__ == "__main__":
    main()
