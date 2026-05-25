#!/bin/bash
set -euo pipefail

export CONDA_NO_PLUGINS=true
export NAVRL_SKIP_NUCLEUS_CHECK=1

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

PROJECT_ROOT="/home/p/CascadeProjects/NavRL/isaac-training"
EVAL_SCRIPT="$PROJECT_ROOT/training/scripts/evaluate_case_stats.py"
RESULT_DIR="$PROJECT_ROOT/media/results"
mkdir -p "$RESULT_DIR"

SCENARIO="${1:-all}"
shift || true

run_eval() {
  local case_name="$1"
  shift
  python "$EVAL_SCRIPT" --case-name "$case_name" --output-dir "$RESULT_DIR" "$@"
}

case "$SCENARIO" in
  static_120)
    run_eval "static_120" \
      env.num_obstacles=120 \
      env_dyn.num_obstacles=0 \
      "$@"
    ;;
  dynamic_120_16)
    run_eval "dynamic_120_16" \
      env.num_obstacles=120 \
      env_dyn.num_obstacles=16 \
      env_dyn.vel_range='[0.2,0.4]' \
      env_dyn.local_range='[3.0,3.0,3.0]' \
      "$@"
    ;;
  dynamic_100_32)
    run_eval "dynamic_100_32" \
      env.num_obstacles=100 \
      env_dyn.num_obstacles=32 \
      "$@"
    ;;
  dynamic_120_32)
    run_eval "dynamic_120_32" \
      env.num_obstacles=120 \
      env_dyn.num_obstacles=32 \
      env_dyn.vel_range='[0.2,0.4]' \
      env_dyn.local_range='[3.0,3.0,3.0]' \
      "$@"
    ;;
  current_config_120_32)
    run_eval "current_config_120_32" \
      env.num_obstacles=120 \
      env_dyn.num_obstacles=32 \
      env_dyn.vel_range='[0.3,0.5]' \
      env_dyn.local_range='[4.0,4.0,3.0]' \
      "$@"
    ;;
  all)
    "$0" static_120 "$@"
    "$0" dynamic_120_16 "$@"
    "$0" dynamic_100_32 "$@"
    "$0" dynamic_120_32 "$@"
    "$0" current_config_120_32 "$@"
    ;;
  *)
    echo "Unsupported scenario: $SCENARIO"
    echo "Supported: static_120, dynamic_120_16, dynamic_100_32, dynamic_120_32, current_config_120_32, all"
    exit 1
    ;;
esac
