#!/usr/bin/env bash
# Inspect E4_screen2 frozen screening: which v4 tasks lock under structured.
set -e
cd /mnt/g/paper0816
python3 - <<'PY'
import json
from pathlib import Path

root = Path("runs/E4_screen2")
for seed in (0, 1):
    p = root / f"seed{seed}" / "repair_structured" / "metrics.jsonl"
    print(f"--- seed{seed} structured ---")
    for ln in p.read_text(encoding="utf-8").splitlines():
        r = json.loads(ln)
        flag = "LOCK" if (not r["success"] and r["repetition_events"] >= 2) else ""
        print(f'{r["instance_id"]:8s} success={r["success"]} '
              f'rep={r["repetition_events"]} {flag}')
PY
