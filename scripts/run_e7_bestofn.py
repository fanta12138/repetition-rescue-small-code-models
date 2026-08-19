"""E7: compute-matched best-of-N baseline (preregistered 2026-08-18).

Preregistration summary (analysis/RESEARCH_LOG.md, frozen before any E7
data was observed):

Loop phase
    Run repair_structured / repair_diverse / repair_nudge_weak on the
    chosen dataset with 5 seeds, identical protocol to E4v4. Output:
    runs/E7/<dataset>/seed<k>/<mode>/metrics.jsonl

Best-of-N phase
    Per instance i (per loop seed k), sample one-shot candidates
    sequentially until cumulative tokens >= the paired diverse-arm token
    spend T_i (hard cap N_max). Two preregistered diversity regimes:
        bestofn_seed : seeds 0..N-1, temperature 0.2 (paper's regime)
        bestofn_temp : no seed, temperature 0.8 (standard best-of-N)
    Success = any sampled candidate passes. The unique-candidate ratio
    (hash-distinct / sampled) is recorded as the preregistered diversity
    audit and reported regardless of outcome.

Usage:
    python -m scripts.run_e7_bestofn --config configs/e7.yaml \
        --dataset v2 --phase loop --seeds 0,1,2,3,4
    python -m scripts.run_e7_bestofn --config configs/e7.yaml \
        --dataset v2 --phase bestofn --seeds 0,1,2,3,4
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
from pathlib import Path

import yaml

from agent.llm import LLMClient
from agent.loop import RepairLoop
from agent.prompts import build_direct_messages
from agent.trajectory import TrajectoryLogger
from tools.patch_utils import extract_code_block
from tools.sandbox import run_pytest


def _load_tasks(dataset: str, limit: int | None):
    if dataset == "v2":
        from data.selfbuilt.tasks_v2 import TASKS
    elif dataset == "v4":
        from data.selfbuilt.tasks_v4 import TASKS
    else:
        raise SystemExit(f"E7 supports v2/v4, got {dataset}")
    return TASKS[: limit or len(TASKS)]


def run_loop_phase(cfg: dict, dataset: str, seeds: list[int],
                   out_root: Path, limit: int | None = None,
                   modes: list[str] | None = None) -> None:
    """Three loop arms, protocol identical to E4v4."""
    tasks = _load_tasks(dataset, limit or cfg["tasks"].get("selfbuilt_limit"))
    llm_cfg = cfg["llm"]
    modes = modes or cfg["modes"]
    for seed in seeds:
        llm = LLMClient(
            base_url=llm_cfg["base_url"], api_key=llm_cfg.get("api_key", "EMPTY"),
            model=llm_cfg["model"], temperature=llm_cfg.get("temperature", 0.2),
            max_tokens=llm_cfg.get("max_tokens", 4096), seed=seed,
        )
        seed_root = out_root / f"seed{seed}"
        seed_root.mkdir(parents=True, exist_ok=True)
        print(f"\n########## [loop] seed={seed} ##########")
        for mode in modes:
            mode_dir = seed_root / mode
            mode_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n===== mode={mode} | tasks={len(tasks)} =====")
            with TrajectoryLogger(mode_dir / "trajectories.jsonl") as logger:
                loop = RepairLoop(cfg, llm, logger)
                rows = [loop.run(t, mode) for t in tasks]
            with open(mode_dir / "metrics.jsonl", "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(f"[{mode}] done: "
                      f"{sum(r['success'] for r in rows)}/{len(rows)} pass")


def _eval_candidate(task: dict, code: str, sandbox_cfg: dict) -> bool:
    workdir = Path(tempfile.mkdtemp(prefix=f"e7_{task['task_id']}_"))
    (workdir / "solution.py").write_text(code, encoding="utf-8")
    (workdir / "test_solution.py").write_text(task["test_code"], encoding="utf-8")
    result = run_pytest(
        workdir, timeout_sec=sandbox_cfg.get("timeout_sec", 20),
        backend=sandbox_cfg.get("backend", "subprocess"),
        docker_image=sandbox_cfg.get("docker_image", "python:3.11-slim"),
    )
    return result.passed


def run_bestofn_phase(cfg: dict, dataset: str, seeds: list[int],
                      out_root: Path) -> None:
    tasks = {t["task_id"]: t for t in _load_tasks(dataset, None)}
    llm_cfg = cfg["llm"]
    sandbox_cfg = cfg.get("sandbox", {})
    n_max = cfg.get("bestofn", {}).get("n_max", 10)
    temp_regime = cfg.get("bestofn", {}).get("temp_regime_temperature", 0.8)

    regimes = {
        # regime -> (temperature, seed_for(sample_idx) )
        "bestofn_seed": (llm_cfg.get("temperature", 0.2), lambda j: j),
        "bestofn_temp": (temp_regime, lambda j: None),
    }

    for seed in seeds:
        budget_path = out_root / f"seed{seed}" / "repair_diverse" / "metrics.jsonl"
        if not budget_path.exists():
            raise SystemExit(f"missing loop-phase budgets: {budget_path}; "
                             f"run --phase loop first")
        budgets = {json.loads(ln)["instance_id"]: json.loads(ln)["total_tokens"]
                   for ln in budget_path.read_text(encoding="utf-8").splitlines()}

        for regime, (temp, seed_fn) in regimes.items():
            reg_dir = out_root / f"seed{seed}" / regime
            reg_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n===== [bestofn] seed={seed} regime={regime} =====")
            rows = []
            for iid, budget in budgets.items():
                task = tasks[iid]
                t0 = time.time()
                samples, tokens_used, success, passed_at = [], 0, False, None
                for j in range(n_max):
                    llm = LLMClient(
                        base_url=llm_cfg["base_url"],
                        api_key=llm_cfg.get("api_key", "EMPTY"),
                        model=llm_cfg["model"], temperature=temp,
                        max_tokens=llm_cfg.get("max_tokens", 4096),
                        seed=seed_fn(j),
                    )
                    resp = llm.generate(build_direct_messages(
                        task["description"], task["buggy_code"]))
                    tokens_used += resp.total_tokens
                    code = extract_code_block(resp.text)
                    candidate = code if code is not None else resp.text
                    ok = _eval_candidate(task, candidate, sandbox_cfg) \
                        if code is not None else False
                    samples.append({
                        "sample": j, "seed": seed_fn(j),
                        "tokens": resp.total_tokens, "passed": ok,
                        "hash": hashlib.sha1(candidate.encode()).hexdigest()[:12],
                    })
                    if ok and not success:
                        success, passed_at = True, j
                    if tokens_used >= budget:
                        break
                hashes = [s["hash"] for s in samples]
                rows.append({
                    "instance_id": iid, "mode": regime, "loop_seed": seed,
                    "budget_tokens": budget, "tokens_used": tokens_used,
                    "n_samples": len(samples),
                    "n_unique": len(set(hashes)),
                    "unique_ratio": len(set(hashes)) / len(samples),
                    "success": success, "passed_at_sample": passed_at,
                    "wall_time": time.time() - t0, "samples": samples,
                })
                print(f"[{regime}] {iid}: budget={budget} used={tokens_used} "
                      f"n={len(samples)} unique={len(set(hashes))} "
                      f"{'PASS' if success else 'FAIL'}")
            with open(reg_dir / "metrics.jsonl", "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/e7.yaml")
    ap.add_argument("--dataset", choices=["v2", "v4"], required=True)
    ap.add_argument("--phase", choices=["loop", "bestofn", "all"], default="all")
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--limit", type=int, default=None,
                    help="loop-phase task limit (dry-run override)")
    ap.add_argument("--modes", default=None,
                    help="loop-phase modes override (comma-separated)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    seeds = [int(s) for s in args.seeds.split(",")]
    out_root = Path(args.out or cfg["output_dir"]) / args.dataset
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "run_meta.json").write_text(json.dumps({
        "experiment": cfg["experiment"], "dataset": args.dataset,
        "model": cfg["llm"]["model"], "seeds": seeds, "phase": args.phase,
        "bestofn": cfg.get("bestofn", {}),
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    loop_modes = args.modes.split(",") if args.modes else None
    if args.phase in ("loop", "all"):
        run_loop_phase(cfg, args.dataset, seeds, out_root,
                       limit=args.limit, modes=loop_modes)
    if args.phase in ("bestofn", "all"):
        run_bestofn_phase(cfg, args.dataset, seeds, out_root)
    print("\nE7 完成。")


if __name__ == "__main__":
    main()
