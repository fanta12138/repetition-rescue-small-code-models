#!/usr/bin/env bash
# Inspect v3_07 hard-failure trajectories (all arms fail): what did the model do?
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816
python - <<'EOF'
import json
from pathlib import Path

for mode in ["repair", "no_feedback"]:
    seed = 0
    rows = [json.loads(l) for l in
            Path(f"runs/E2/seed{seed}/{mode}/metrics.jsonl").read_text().splitlines()]
    r = next(r for r in rows if r["instance_id"] == "v3_07")
    print(f"=== seed{seed}/{mode}: success={r['success']} iters={r['llm_calls']} "
          f"files_changed={r.get('files_changed')} localized={r.get('localized_bug_file')}")
    for line in Path(f"runs/E2/seed{seed}/{mode}/trajectories.jsonl").read_text(encoding="utf-8").splitlines():
        t = json.loads(line)
        if t.get("instance_id") != "v3_07":
            continue
        ex = t.get("extra", {})
        excerpt = ex.get("response_excerpt", "")
        print(f"  [step {t.get('step')}] feedback head: {str(ex.get('feedback',''))[:200]!r}")
        print(f"      response head: {excerpt[:300]!r}")
    print()
EOF
