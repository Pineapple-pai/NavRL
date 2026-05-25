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
CAPTURE_SCRIPT="$PROJECT_ROOT/capture_demo_videos.sh"
EVAL_SCRIPT="$PROJECT_ROOT/evaluate_demo_cases.sh"

MODE="${1:-all}"
VIDEO_STEPS="${VIDEO_STEPS:-800}"
VIDEO_SEED="${VIDEO_SEED:-0}"
EVAL_SEEDS="${EVAL_SEEDS:-0 1 2 3 4}"
GOAL_HOLD_STEPS="${GOAL_HOLD_STEPS:-5}"

run_videos() {
  bash "$CAPTURE_SCRIPT" static_120_success --max-steps "$VIDEO_STEPS" --seed "$VIDEO_SEED"
  bash "$CAPTURE_SCRIPT" dynamic_120_16_failure_analysis --max-steps "$VIDEO_STEPS" --seed "$VIDEO_SEED"
  bash "$CAPTURE_SCRIPT" dynamic_100_32_stress --max-steps "$VIDEO_STEPS" --seed "$VIDEO_SEED"
  bash "$CAPTURE_SCRIPT" dynamic_120_32_success --max-steps "$VIDEO_STEPS" --seed "$VIDEO_SEED"
}

run_stats() {
  bash "$EVAL_SCRIPT" static_120 --seeds $EVAL_SEEDS --goal-hold-steps "$GOAL_HOLD_STEPS"
  bash "$EVAL_SCRIPT" dynamic_120_16 --seeds $EVAL_SEEDS --goal-hold-steps "$GOAL_HOLD_STEPS"
  bash "$EVAL_SCRIPT" dynamic_100_32 --seeds $EVAL_SEEDS --goal-hold-steps "$GOAL_HOLD_STEPS"
  bash "$EVAL_SCRIPT" dynamic_120_32 --seeds $EVAL_SEEDS --goal-hold-steps "$GOAL_HOLD_STEPS"
}

case "$MODE" in
  videos)
    run_videos
    ;;
  stats)
    run_stats
    ;;
  all)
    run_videos
    run_stats
    ;;
  *)
    echo "Unsupported mode: $MODE"
    echo "Supported: videos, stats, all"
    exit 1
    ;;
esac
