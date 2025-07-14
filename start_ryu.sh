#!/bin/bash

source /data/miniconda3/etc/profile.d/conda.sh
conda activate gjwryu

# 强制使用虚拟环境内的包，彻底屏蔽系统路径
export PYTHONPATH=/data/miniconda3/envs/gjwryu/lib/python3.9/site-packages:$(pwd)

# 明确使用 conda 环境的 Python
/data/miniconda3/envs/gjwryu/bin/python -m ryu.cmd.manager \
  --observe-links \
  ryu.app.ofctl_rest \
  ryu.app.rest_topology \
  ryu.topology.switches \
  backend/controller/PathIntentController.py \
  backend/controller/ryu_topology_rest.py \
  --ofp-tcp-listen-port 6633 \
  --ofp-listen-host 0.0.0.0 \
  --wsapi-port 8081