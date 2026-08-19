#!/usr/bin/env bash
# Diagnose why vLLM reports "UVA is not available" on this WSL2 setup.
set -uo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin"
source "$HOME/agentenv/bin/activate"

echo "=== vllm is_uva_available source ==="
sed -n '40,90p' "$HOME/agentenv/lib/python3.12/site-packages/vllm/utils/platform_utils.py"

echo "=== nvidia-smi ==="
nvidia-smi | head -15

echo "=== torch/uva probe ==="
python - <<'EOF'
import torch
print("torch", torch.__version__, "cuda", torch.version.cuda)
print("dev", torch.cuda.get_device_name(0))
x = torch.zeros(4, pin_memory=True)
try:
    from torch.cuda import cudaHostRegister  # noqa
except Exception:
    pass
try:
    import vllm.utils.platform_utils as pu
    print("vllm is_uva_available:", pu.is_uva_available())
except Exception as e:
    print("vllm probe error:", e)
# direct check: can we map pinned memory into CUDA address space?
try:
    g = x.cuda()
    print("pinned->cuda copy ok:", g.sum().item())
except Exception as e:
    print("pinned->cuda failed:", e)
EOF
