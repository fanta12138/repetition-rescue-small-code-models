#!/usr/bin/env bash
# Compile the paper with latexmk (pdflatex + bibtex, two rounds).
# Run:  wsl -d Ubuntu-24.04 -u root -- bash setup_env/compile_paper.sh
set -u
cd /mnt/g/paper0816/paper || exit 1
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex > /tmp/latexmk.log 2>&1
rc=$?
echo "LATEXMK_RC=$rc"
if [ $rc -ne 0 ]; then
    echo "=== last errors ==="
    grep -A3 -E "^!|Error" main.log | head -40
else
    echo "=== pages ==="
    pdfinfo main.pdf 2>/dev/null | grep -i pages || ls -la main.pdf
    echo "=== undefined refs/cites ==="
    grep -E "Warning.*(undefined|Citation)" main.log | head -10
fi
