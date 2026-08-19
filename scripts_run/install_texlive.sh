#!/usr/bin/env bash
# Install TeX Live toolchain in WSL for paper compilation (slow).
# Run as root:  wsl -d Ubuntu-24.04 -u root -- bash install_texlive.sh
set -uo pipefail
export DEBIAN_FRONTEND=noninteractive
[ "$(id -u)" = "0" ] || { echo "run as root"; exit 1; }
apt-get update -qq
apt-get install -y -qq \
    texlive-latex-base texlive-latex-recommended texlive-latex-extra \
    texlive-fonts-recommended texlive-science texlive-lang-chinese latexmk \
    > /tmp/texlive_install.log 2>&1
echo "exit=$?"
which pdflatex latexmk bibtex
