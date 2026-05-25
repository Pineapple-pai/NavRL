#!/bin/bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate NavRL
export CONDA_NO_PLUGINS=true
export NAVRL_SKIP_NUCLEUS_CHECK=1
export DISPLAY=""

python -u /home/p/CascadeProjects/NavRL/isaac-training/training/scripts/train.py \
  headless=True wandb.mode=disabled "$@"
