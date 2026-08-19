#!/usr/bin/env bash
# Extract the already-downloaded HumanEval.jsonl.gz from modelscope cache.
set -e
source ~/agentenv/bin/activate
python - <<'EOF'
import gzip
import json
import shutil
from pathlib import Path

src = Path.home() / ".cache/modelscope/hub/datasets/downloads/6446f27f3bdeb99626030cbb73b87450601708115f4bde4292d233e14041d297"
dst = Path("/mnt/g/paper0816/data/humaneval.jsonl")
with gzip.open(src, "rb") as fin, dst.open("wb") as fout:
    shutil.copyfileobj(fin, fout)

rows = [json.loads(line) for line in dst.read_text(encoding="utf-8").splitlines()]
print("rows:", len(rows))
print("cols:", sorted(rows[0].keys()))
assert len(rows) == 164
assert all(k in rows[0] for k in ("task_id", "prompt", "entry_point", "test", "canonical_solution"))
print("OK ->", dst)
EOF
