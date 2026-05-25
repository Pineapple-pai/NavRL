#!/bin/bash
set -euo pipefail

export CONDA_NO_PLUGINS=true

CONDA_BIN="${CONDA_EXE:-$(command -v conda)}"
if [ -z "$CONDA_BIN" ]; then
  echo "Conda executable not found."
  exit 1
fi

CONDA_ROOT="$(dirname "$(dirname "$CONDA_BIN")")"
CONDA_ACTIVATE="$CONDA_ROOT/bin/activate"
CONDA_ENV_PATH="$CONDA_ROOT/envs/NavRL"
if [ ! -f "$CONDA_ACTIVATE" ]; then
  echo "Conda activate script not found at: $CONDA_ACTIVATE"
  exit 1
fi
if [ ! -d "$CONDA_ENV_PATH" ]; then
  echo "NavRL environment not found at: $CONDA_ENV_PATH"
  exit 1
fi

unset CONDA_PREFIX CONDA_DEFAULT_ENV CONDA_PROMPT_MODIFIER CONDA_SHLVL _CE_M _CE_CONDA
source "$CONDA_ACTIVATE" "$CONDA_ENV_PATH"

export NAVRL_SKIP_NUCLEUS_CHECK=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __NV_PRIME_RENDER_OFFLOAD=1
export __VK_LAYER_NV_optimus=NVIDIA_only
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json
export DISPLAY=:0

PROJECT_ROOT="/home/p/CascadeProjects/NavRL/isaac-training"
EXPORT_SCRIPT="$PROJECT_ROOT/training/scripts/export_demo_video.py"
MEDIA_DIR="$PROJECT_ROOT/media"
mkdir -p "$MEDIA_DIR"

SCENARIO="${1:-all}"
shift || true

run_export() {
  local output_name="$1"
  local screenshot_name="$2"
  shift
  shift
  python "$EXPORT_SCRIPT" \
    --output "$MEDIA_DIR/$output_name" \
    --screenshot-output "$MEDIA_DIR/$screenshot_name" \
    --num-envs 20 \
    "$@"
}

case "$SCENARIO" in
  static_120_success)
    run_export "static_120_baseline.mp4" "static_120_baseline.png" \
      env.num_obstacles=120 \
      env_dyn.num_obstacles=0 \
      sim.dt=0.05 \
      "$@"
    ;;
  dynamic_120_16_failure_analysis)
    run_export "dynamic_120_16_medium_density.mp4" "dynamic_120_16_medium_density.png" \
      env.num_obstacles=120 \
      env_dyn.num_obstacles=16 \
      env_dyn.vel_range='[0.2,0.4]' \
      env_dyn.local_range='[3.0,3.0,3.0]' \
      sim.dt=0.05 \
      "$@"
    ;;
  dynamic_120_32_success)
    run_export "dynamic_120_32_high_density_mixed.mp4" "dynamic_120_32_high_density_mixed.png" \
      env.num_obstacles=120 \
      env_dyn.num_obstacles=32 \
      env_dyn.vel_range='[0.2,0.4]' \
      env_dyn.local_range='[3.0,3.0,3.0]' \
      sim.dt=0.05 \
      "$@"
    ;;
  dynamic_100_32_stress)
    run_export "dynamic_100_32_stress_test.mp4" "dynamic_100_32_stress_test.png" \
      env.num_obstacles=100 \
      env_dyn.num_obstacles=32 \
      sim.dt=0.05 \
      "$@"
    ;;
  current_config_120_32_v035_05_local443)
    run_export "current_config_120_32_v035_05_local443.mp4" "current_config_120_32_v035_05_local443.png" \
      env.num_obstacles=120 \
      env_dyn.num_obstacles=32 \
      env_dyn.vel_range='[0.3,0.5]' \
      env_dyn.local_range='[4.0,4.0,3.0]' \
      sim.dt=0.05 \
      "$@"
    ;;
  post_avoidance_stability_before_after)
    run_export "post_avoidance_stability_after.mp4" "post_avoidance_stability_after.png" \
      env.num_obstacles=120 \
      env_dyn.num_obstacles=32 \
      env_dyn.vel_range='[0.2,0.4]' \
      env_dyn.local_range='[3.0,3.0,3.0]' \
      sim.dt=0.05 \
      "$@"
    ;;
  all)
    "$0" static_120_success "$@"
    "$0" dynamic_120_16_failure_analysis "$@"
    "$0" dynamic_100_32_stress "$@"
    "$0" dynamic_120_32_success "$@"
    "$0" current_config_120_32_v035_05_local443 "$@"
    ;;
  *)
    echo "Unsupported scenario: $SCENARIO"
    echo "Supported: static_120_success, dynamic_120_16_failure_analysis, dynamic_100_32_stress, dynamic_120_32_success, post_avoidance_stability_before_after, current_config_120_32_v035_05_local443, all"
    exit 1
    ;;
esac
