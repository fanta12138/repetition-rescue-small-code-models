#!/usr/bin/env bash
# Download Qwen2.5-Coder-3B-Instruct-AWQ (~2GB) for E6 cross-model validation.
# Source: ModelScope (huggingface.co blocked in this network). Resume-safe.
set -e
export PATH=~/.local/bin:$PATH
. ~/agentenv/bin/activate
mkdir -p ~/models
modelscope download --model Qwen/Qwen2.5-Coder-3B-Instruct-AWQ \
    --local_dir ~/models/Qwen2.5-Coder-3B-Instruct-AWQ
echo "DOWNLOAD_3B_DONE"
du -sh ~/models/Qwen2.5-Coder-3B-Instruct-AWQ
