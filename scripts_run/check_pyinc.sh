#!/usr/bin/env bash
readlink -f ~/agentenv/bin/python
~/agentenv/bin/python -c "import sysconfig; print('include:', sysconfig.get_paths()['include'])"
INC=$(~/agentenv/bin/python -c "import sysconfig; print(sysconfig.get_paths()['include'])")
ls "$INC" 2>&1 | head -5
echo "---"
ls /usr/include/python3.12 2>&1 | head -3
echo "---"
ls ~/.local/share/uv/python/ 2>&1
