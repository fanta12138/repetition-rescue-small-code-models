#!/usr/bin/env bash
# E3 analysis: per-dataset metrics + pooled McNemar (preregistered) +
# locked-subset recovery + regression guard.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816

echo "===== metrics (v2) ====="
python -m eval.metrics --run runs/E3v2
echo
echo "===== metrics (v3) ====="
python -m eval.metrics --run runs/E3v3
echo
echo "===== McNemar per dataset ====="
python -m eval.stat_test --run runs/E3v2 \
    --pairs repair_diverse:repair_structured repair_tempbump:repair_structured
python -m eval.stat_test --run runs/E3v3 \
    --pairs repair_diverse:repair_structured repair_tempbump:repair_structured
echo
echo "===== POOLED (v2+v3, preregistered primary) + locked subset ====="
python - <<'EOF'
import json
from pathlib import Path
from eval.stat_test import load_mode, mcnemar_exact, wilson_interval

def pooled(mode_a, mode_b):
    res_a, res_b = {}, {}
    for root in [Path("runs/E3v2"), Path("runs/E3v3")]:
        res_a.update(load_mode(root, mode_a))
        res_b.update(load_mode(root, mode_b))
    keys = sorted(set(res_a) & set(res_b))
    b = sum(1 for k in keys if res_a[k] and not res_b[k])
    c = sum(1 for k in keys if res_b[k] and not res_a[k])
    n = len(keys)
    pa = sum(res_a[k] for k in keys) / n
    pb = sum(res_b[k] for k in keys) / n
    p = mcnemar_exact(b, c)
    lo, hi = wilson_interval(b, b + c) if (b + c) else (0.0, 0.0)
    sig = p < 0.025 and (pa - pb) >= 0.04   # preregistered: Bonferroni + 4pp
    print(f"[POOLED {mode_a} vs {mode_b}] n={n}: {pa:.1%} vs {pb:.1%} "
          f"diff={pa-pb:+.1%}, discordant {b}/{c}, p={p:.4f}"
          f"{'  -> PASS preregistered threshold' if sig else '  -> below threshold'}")
    return res_a, res_b, keys

for arm in ["repair_diverse", "repair_tempbump"]:
    res_a, res_b, keys = pooled(arm, "repair_structured")
    # regression guard: losses on non-locked instances
    losses = [k for k in keys if res_b[k] and not res_a[k]]
    print(f"  regression guard: losses vs repair_structured = {losses or 'none'}")
    # locked subset: instances where repair_structured failed
    locked = [k for k in keys if not res_b[k]]
    rec = [k for k in locked if res_a[k]]
    print(f"  locked subset (structured failed): {len(locked)} instances "
          f"{sorted(k[1] for k in locked)}")
    print(f"  recovered by {arm}: {len(rec)} {sorted(k[1] for k in rec)}")
    print()
EOF
echo
echo "===== task matrix (v2) ====="
python -m scripts.task_matrix runs/E3v2
echo
echo "===== task matrix (v3) ====="
python -m scripts.task_matrix runs/E3v3
