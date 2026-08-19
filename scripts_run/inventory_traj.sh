#!/usr/bin/env bash
# Inventory which lock-case trajectories exist where (for AST analysis).
set -uo pipefail
cd /mnt/g/paper0816
for d in E3v2 E4v2lock E4v4 E5 E6lock; do
  echo "== $d"
  ls runs/$d/seed0/ 2>/dev/null
done
echo "--- sample metrics row (E4v4 structured) ---"
head -c 400 runs/E4v4/seed0/repair_structured/metrics.jsonl 2>/dev/null
echo
echo "--- truncation check: coder excerpts at 2000 chars ---"
python3 - <<'EOF'
import json
from pathlib import Path
hits = []
for p in Path("runs").glob("*/*/*/trajectories.jsonl"):
    for line in p.read_text(errors="ignore").splitlines():
        t = json.loads(line)
        ex = t.get("extra", {}).get("response_excerpt", "") if t.get("extra") else ""
        if len(ex) >= 1999:
            hits.append((str(p), t["instance_id"], t["step"]))
for h in hits[:20]:
    print(h)
print("total truncated coder rows:", len(hits))
EOF
