#!/usr/bin/env bash
# E6 one-shot pipeline inside ONE long-lived WSL session (keeps the distro
# alive): start vLLM 3B-AWQ, wait for ready, run all E6 runs, then analyze.
set -uo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"
cd /mnt/g/paper0816

pkill -f "vllm serve" 2>/dev/null || true
sleep 5
mkdir -p logs
# vLLM 0.27 disables pinned memory on WSL2 by default; the new V1 GPU worker
# requires UVA (built on pinned memory), so this flag is mandatory here.
export VLLM_WSL2_ENABLE_PIN_MEMORY=1
VLLM_LOG=/mnt/g/paper0816/logs/vllm_3b.log
rm -f "$VLLM_LOG"

vllm serve "$HOME/models/Qwen2.5-Coder-3B-Instruct-AWQ" \
    --served-model-name Qwen/Qwen2.5-Coder-3B-Instruct-AWQ \
    --quantization awq --max-model-len 16384 \
    --gpu-memory-utilization 0.9 --port 8000 \
    > "$VLLM_LOG" 2>&1 &
VLLM_PID=$!
echo "vllm pid=$VLLM_PID"

READY=0
for i in $(seq 1 60); do
    code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/v1/models || true)
    if [ "$code" = "200" ]; then
        echo "VLLM_3B_READY after ${i}0s"
        curl -s http://localhost:8000/v1/models
        READY=1
        break
    fi
    if ! kill -0 "$VLLM_PID" 2>/dev/null; then
        echo "VLLM_DIED; EngineCore error lines:"
        grep -nE "ERROR|Traceback|raise |RuntimeError|CUDA|cuda|Error:" "$VLLM_LOG" | grep -viE "shutdown" | head -40
        echo "--- full tail ---"
        tail -80 "$VLLM_LOG"
        exit 1
    fi
    sleep 10
done
if [ "$READY" != "1" ]; then
    echo "VLLM_3B_NOT_READY after 600s; log tail:"
    tail -60 "$VLLM_LOG"
    exit 1
fi

echo "=== E6 RUNS START ==="
bash /mnt/g/paper0816/setup_env/run_e6.sh
RUN_RC=$?
echo "=== E6 RUNS DONE rc=$RUN_RC ==="

echo "=== E6 ANALYZE START ==="
bash /mnt/g/paper0816/setup_env/analyze_e6.sh
ANA_RC=$?
echo "=== E6 ANALYZE DONE rc=$ANA_RC ==="

kill "$VLLM_PID" 2>/dev/null || true
echo "E6_PIPELINE_COMPLETE run=$RUN_RC analyze=$ANA_RC"
