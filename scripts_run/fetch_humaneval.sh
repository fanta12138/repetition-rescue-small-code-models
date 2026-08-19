#!/usr/bin/env bash
set -e
export PATH=~/.local/bin:$PATH
source ~/agentenv/bin/activate

python - <<'EOF'
import json
from pathlib import Path

from modelscope.msdatasets import MsDataset

ds = MsDataset.load("modelscope/humaneval", split="test", trust_remote_code=True)
print("rows:", len(ds), "cols:", list(ds[0].keys()))

out = Path("/mnt/g/paper0816/data/humaneval.jsonl")
with out.open("w", encoding="utf-8") as f:
    for row in ds:
        f.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
print("saved:", out)
EOF
