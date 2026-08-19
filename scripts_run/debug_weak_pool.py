#!/usr/bin/env python3
"""Debug: which instances enter the 7B weak locked-only pool."""
import json
from pathlib import Path

ROOT = Path("/mnt/g/paper0816/runs")
SRC = [("E4v2lock", range(5)), ("E4v3lock", range(5)),
       ("E4v4", range(5)), ("E5", range(2))]


def load(run, seed, arm):
    p = ROOT / run / f"seed{seed}" / arm / "metrics.jsonl"
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            out[r["instance_id"]] = r
    return out


for run, seeds in SRC:
    for s in seeds:
        st = load(run, s, "repair_structured")
        wk = load(run, s, "repair_nudge_weak")
        for tid, row in sorted(wk.items()):
            srow = st.get(tid)
            locked = srow and (not srow["success"]) and srow.get(
                "repetition_events", 0) >= 2
            if locked:
                print(run, "s%d" % s, tid,
                      "rep_struct=%d" % srow.get("repetition_events", -1),
                      "weak_ok=%d" % row["success"],
                      "weak_iter=%d" % row["iterations"],
                      "weak_tok=%d" % row["total_tokens"])
