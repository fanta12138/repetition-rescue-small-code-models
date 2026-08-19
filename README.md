# Repetition Rescue, Not Diagnostic Feedback: A Controlled Dissection of Self-Repair in Small Code Models

Data and code release for the paper *"Repetition Rescue, Not
Diagnostic Feedback: A Controlled Dissection of Self-Repair in Small
Code Models"* (IEEE Access), by **Peng Deng, Hong Li, and Yuanwu
Zhou** (School of Civil and Architectural Engineering, Guangxi
University of Science and Technology).

Corresponding author: Peng Deng (dengpeng@gxust.edu.cn,
ORCID: [0000-0002-2892-4251](https://orcid.org/0000-0002-2892-4251)).

## What this repository contains

Everything needed to recompute every number in the paper:

| Directory | Content |
|-----------|---------|
| `preregistration/` | `RESEARCH_LOG.md` — the single preregistration record. Decision rules for every experiment were frozen in this file **before** the corresponding data were collected (in Chinese). |
| `configs/` | Per-experiment YAML configs (token budgets, iteration caps, arms, seeds, model endpoints). |
| `agent/` | The repair-loop harness: feedback compression, prompts, loop control, trajectory logging. |
| `eval/` | Metrics and pre-registered statistical tests (exact McNemar with doubling method). |
| `tools/` | Sandboxed test execution (subprocess/docker) and SWE-style adapters. |
| `data/selfbuilt/` | The self-built Python unit-test debug suites v1–v5 (`tasks.py` … `tasks_v5.py`); `data/humaneval.jsonl` is the standard HumanEval set used in E8. |
| `runs/` | **Raw per-instance logs for all 21 experiment directories** (`metrics.jsonl` + `trajectories.jsonl` per arm). All paper numbers are recomputed from these files. |
| `analysis/` | Post-hoc analysis scripts and audit scripts; `figures_data/` holds the Bayes-factor and AST-distance CSVs used by the paper. |
| `scripts/` | Experiment entry points (`run_e0.py`, `run_e7_bestofn.py`, `run_e8_humaneval.py`, …) and figure/analysis drivers. |
| `scripts_run/` | Shell scripts actually used to serve vLLM and execute each experiment (WSL2 environment). |
| `figures/` | Paper figures as PDF/PNG plus the matching CSV data for each figure. |

## Experiment → run-directory map

Paper numbers are recomputed from `runs/<dir>/<arm>/metrics.jsonl`:

| Paper experiment | Run directories |
|------------------|-----------------|
| E0 feedback dissection (7B, 5 seeds × 4 arms) | `E0v2s5` (main); pilots `E0`, `E0v2`, `E0v2s` |
| E1 feedback format arms | `E1` |
| E2 v3 multi-file suite | `E2` |
| E3 lock-breaking intervention screens | `E3v2`, `E3v3` (+ smoke `E3_smoke_v2/v3`) |
| E4 sticky-suite (v4) intervention + attribution | `E4v2lock`, `E4v3lock`, `E4v4`, `E4_screen`, `E4_screen2` |
| E5 shallow-lock extension (v5) | `E5`, `E5_screen` |
| E6 3B replication | `E6v2`, `E6lock` |
| E7 best-of-n compute-anchored baseline | `E7` |
| E8 HumanEval lock-in prevalence | `E8` |

## Reproduction

1. Serve the model (RTX 3090, 24 GB) inside WSL2:

   ```bash
   vllm serve Qwen2.5-Coder-7B-Instruct-AWQ --quantization awq \
     --max-model-len 16384 --gpu-memory-utilization 0.9 --port 8000
   ```

   (3B arm of E6 uses `Qwen2.5-Coder-3B-Instruct-AWQ` with a
   pin-memory workaround for WSL2 UVA; see
   `scripts_run/start_vllm_3b.sh` and `scripts_run/serve_3b.sh`.)

2. `pip install -r requirements.txt`
3. Run an experiment, e.g. `python scripts/run_e0.py --config configs/e0_pilot.yaml`
   (each config pins temperature 0.2, 5 iterations, and the
   per-instance token budget).
4. Recompute statistics exactly as in the paper with
   `eval/stat_test.py`, `scripts_run/bayes_factors.py`, and
   `scripts_run/ast_structure_distance.py`; regenerate figures with
   `scripts_run/make_figures.py` (matplotlib, Times New Roman; each
   figure has a matching CSV in `figures/`).

## Provenance notes

- `configs/e0_pilot.yaml` references `data/swe_pilot_subset.jsonl`;
  that SWE-bench pilot track was dropped during E0 development and
  the file was never created — the final E0 results use only the
  self-built suites, as reported in the paper.
- Smoke runs (`E3_smoke_v2`, `E3_smoke_v3`) are included for full
  transparency; no paper number is drawn from them.

## License

All data, logs, and the preregistration record are licensed under the
**Creative Commons Attribution 4.0 International License (CC-BY 4.0)**
— <https://creativecommons.org/licenses/by/4.0/> — matching the
license of the open-access paper. The Python source code in this
repository is licensed under the **MIT License** (see `LICENSE`).
