"""Dump coder-step excerpts for a given instance from E0v2 trajectories."""
import json
import sys
from pathlib import Path

tid = sys.argv[1] if len(sys.argv) > 1 else "v2_11"
run = Path("runs/E0v2")
for mode_dir in sorted(run.iterdir()):
    traj = mode_dir / "trajectories.jsonl"
    if not traj.exists():
        continue
    print(f"\n===== {mode_dir.name} =====")
    for line in traj.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["instance_id"] != tid or row.get("role") != "coder":
            continue
        excerpt = (row.get("extra") or {}).get("response_excerpt", "")
        one_line = " | ".join(excerpt.splitlines())
        print(f"step {row['step']}: {one_line[:260]}")
