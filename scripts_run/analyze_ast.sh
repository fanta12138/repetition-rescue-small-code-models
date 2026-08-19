#!/usr/bin/env bash
# Offline AST structural-distance analysis (no model calls).
# Computes de-identifier AST structure sequences for every coder step of the
# lock cases, pairwise Levenshtein distances, and per-task classification
# (family-switch vs within-family tinkering). Outputs:
#   analysis/figures_data/ast_structure_distance.csv   (per-step rows)
#   analysis/figures_data/ast_case_matrix.csv          (per-case summary)
# Prints the case summary to stdout.
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
cd /mnt/g/paper0816
python3 setup_env/ast_structure_distance.py
