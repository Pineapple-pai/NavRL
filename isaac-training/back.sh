#!/bin/bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate NavRL
export CONDA_NO_PLUGINS=true
export NAVRL_SKIP_NUCLEUS_CHECK=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __NV_PRIME_RENDER_OFFLOAD=1
export __VK_LAYER_NV_optimus=NVIDIA_only
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json
export DISPLAY=:0

python /home/p/CascadeProjects/NavRL/isaac-training/training/scripts/eval.py \
  headless=False wandb.mode=disabled sim.dt=0.05 "$@"
