#!/usr/bin/env bash
# Forensics on E6lock v4_08 rescue rows: full response vs 7B, model fields.
set -uo pipefail
cd /mnt/g/paper0816
python3 - <<'EOF'
import hashlib, json
from pathlib import Path

def rows(run, seed, arm, tid, role="coder"):
    p = Path(f"runs/{run}/seed{seed}/{arm}/trajectories.jsonl")
    out = []
    for line in p.read_text(errors="ignore").splitlines():
        t = json.loads(line)
        if t["instance_id"] == tid and t.get("role") == role:
            out.append(t)
    return out

def sig(rs):
    return [(r.get("step"), sorted((r.get("extra") or {}).keys()),
             len(str(r.get("response", r.get("content", "")))),
             hashlib.md5(str(r.get("response", r.get("content", ""))).encode()).hexdigest()[:8])
            for r in rs]

r7 = rows("E4v4", 0, "repair_diverse", "v4_08")
print("7B coder rows:", sig(r7))
print("7B extra keys sample:", (r7[-1].get("extra") or {}).keys() if r7 else None)
for s in (2, 3, 4):
    r3 = rows("E6lock", s, "repair_diverse", "v4_08")
    print(f"3B s{s} coder rows:", sig(r3))
# top-level keys of one row
print("top-level keys:", sorted(r7[-1].keys()) if r7 else None)
print("3B top-level keys:", sorted(rows("E6lock", 2, "repair_diverse", "v4_08")[-1].keys()))
# any model field anywhere?
sample = rows("E6lock", 2, "repair_diverse", "v4_08")[-1]
print("sample row:", json.dumps(sample, ensure_ascii=False)[:600])
EOF
