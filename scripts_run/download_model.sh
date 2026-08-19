#!/usr/bin/env bash
# Download Qwen2.5-Coder-7B-Instruct-AWQ (~4.7GB) into WSL home (fast ext4 disk).
# Source: ModelScope (huggingface.co / hf-mirror.com are blocked in this network).
# Resume-safe: re-run continues partial downloads.
set -e
export PATH=~/.local/bin:$PATH
. ~/agentenv/bin/activate
uv pip install -q modelscope
mkdir -p ~/models
modelscope download --model Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
    --local_dir ~/models/Qwen2.5-Coder-7B-Instruct-AWQ
echo "DOWNLOAD_DONE"
du -sh ~/models/Qwen2.5-Coder-7B-Instruct-AWQ
