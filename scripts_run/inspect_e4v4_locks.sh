#!/usr/bin/env bash
# E4v4 main-run locked seed-instances (frozen E7 P1 locked set source).
set -e
cd /mnt/g/paper0816
python3 - <<'PY'
import json
from pathlib import Path

root = Path("runs/E4v4")
locked = []
for seed in range(5):
    p = root / f"seed{seed}" / "repair_structured" / "metrics.jsonl"
    for ln in p.read_text(encoding="utf-8").splitlines():
        r = json.loads(ln)
        if not r["success"] and r["repetition_events"] >= 2:
            locked.append((r["instance_id"], seed))
print("E4v4 locked seed-instances (structured, rep>=2):")
for iid, seed in sorted(locked):
    print(f"  {iid} @ seed{seed}")
print(f"total: {len(locked)} units over {len(set(i for i,_ in locked))} tasks")
PY
