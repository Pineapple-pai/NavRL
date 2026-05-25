# NavRL Isaac Training Project Showcase

## Project Summary

This subproject documents a reinforcement learning workflow for quadrotor navigation in mixed static and dynamic obstacle environments using `NavRL`, `Isaac Sim 4.x`, and `PPO`.

The main goal of this work was not to redesign the whole NavRL algorithm, but to make the Isaac-training pipeline actually usable for iterative training, debugging, evaluation, and project presentation under the local development environment.

The project focused on four practical problems:

- reducing the drone's tendency to escape diagonally around the map instead of crossing the obstacle field
- preserving static-obstacle navigation ability after introducing dynamic obstacles
- improving post-avoidance flight stability when the drone starts wobbling after the first evasive maneuver
- making training and replay stable enough to support repeated experiments and visual inspection

## Why This Project Matters

Dynamic obstacle avoidance is closer to real deployment scenarios than pure static map navigation. In real environments, a UAV must avoid shelves, walls, poles, and also moving people, vehicles, or robots. Compared with classic replanning-only pipelines, reinforcement learning can provide faster local reaction in cluttered, partially changing environments.

This project demonstrates a full loop of:

- simulator-based training
- environment design and reward shaping
- debugging policy failure modes from replay
- staged curriculum design from static to dynamic obstacles
- turning research code into a presentable engineering project

## Tech Stack

- `Python 3.10`
- `Isaac Sim 4.x`
- `PyTorch`
- `TorchRL`
- `Hydra`
- `Weights & Biases` (disabled locally during most runs)
- `NavRL` upstream codebase
- `OmniDrones` controller stack

## Problem Setup

The drone is trained to navigate from one side of the map to the other while avoiding:

- static obstacles generated in the environment
- dynamic obstacles moving within a local range

### Observation Inputs

The policy consumes:

- drone state
- LiDAR observation
- goal direction
- dynamic obstacle features

### Action Output

The policy outputs a velocity target which is converted by:

- `VelController`
- `LeePositionController`

into low-level actuator commands.

## What I Changed

The following changes were made on top of the upstream training pipeline.

### 1. Reset distribution to force real obstacle crossing

File:

- `training/scripts/env.py`

Key idea:

- constrain the drone start and goal to opposite sides of the map
- reduce lateral freedom so the drone cannot cheaply bypass the obstacle field by flying diagonally along the boundary
- initialize yaw to face the goal direction

Impact:

- reduced the diagonal-escape behavior
- made the policy actually learn obstacle crossing instead of map-edge exploitation

### 2. Reward shaping for stability after the first avoidance maneuver

File:

- `training/scripts/env.py`

Key idea:

- keep forward-progress reward and safety reward
- add penalties for angular velocity and throttle change
- discourage unstable wobbling after the first evasive maneuver

Impact:

- reduced unstable flight after initial obstacle avoidance
- improved follow-up collision behavior in mixed environments

### 3. Dynamic obstacle spawn protection near start/goal corridors

File:

- `training/scripts/env.py`

Key idea:

- prevent dynamic obstacles from spawning inside protected start/goal corridor regions
- avoid training collapse caused by immediate blockage near the takeoff or goal area

Impact:

- improved curriculum smoothness when dynamic obstacles were introduced
- reduced early episode failures caused by unreasonable scene generation

### 4. Safer dynamic obstacle parameter handling

File:

- `training/scripts/env.py`

Key idea:

- add a validity check for unsupported low `env_dyn.num_obstacles` values
- prevent zero-division-style failures in the dynamic obstacle generation logic

Impact:

- improved robustness of experiment setup
- made bad configurations fail fast with a clear error

### 5. Training and replay workflow improvements

Files:

- `training/scripts/train.py`
- `back.sh`

Key idea:

- improve checkpoint resume behavior
- make step counting easier to interpret during resumed training
- add replay-side GPU/Vulkan environment setup for more stable Isaac Sim rendering

Impact:

- easier iterative training
- easier inspection of policy behavior through replay

## Quantified Results

The table below summarizes the key milestone results that were explicitly observed during experiments.

> Note: only configurations with concrete observed outcomes from the experiment history are listed numerically. Some intermediate stages were evaluated qualitatively rather than logged as a strict percentage.

| Stage | Configuration | Main Observation | Result |
| --- | --- | --- | --- |
| Static baseline | `env.num_obstacles=120`, `env_dyn.num_obstacles=0` | Stable static obstacle crossing | `~80% to 90%` pass rate |
| Medium dynamic density | `env.num_obstacles=120`, `env_dyn.num_obstacles=16`, `vel_range=[0.2, 0.4]`, `local_range=[3.0, 3.0, 3.0]` | Dynamic interference starts to destabilize post-avoidance flight | `~50% to 60%` pass rate |
| Dynamic stress test | `env.num_obstacles=100`, `env_dyn.num_obstacles=32` | Dynamic obstacles expose weak dynamic-avoidance generalization | `~50%` pass rate |
| High-density mixed scene | `env.num_obstacles=120`, `env_dyn.num_obstacles=32`, `vel_range=[0.2, 0.4]`, `local_range=[3.0, 3.0, 3.0]` | After staged curriculum and stability reward fixes, mixed navigation becomes significantly more stable | `~70%` pass rate |

### Additional Qualitative Findings

- `env.num_obstacles=160` in pure static scenes was only partially passable.
- `env.num_obstacles=200` in pure static scenes caused many drones to get stuck near the final obstacles.
- `env.num_obstacles=50`, `env_dyn.num_obstacles=64` caused a strong performance drop, suggesting the policy still degrades under very high dynamic density.
- In many dynamic-scene failures, the final collision was with a static obstacle, indicating that dynamic disturbance often breaks trajectory stability before causing a direct dynamic collision.

## Current Training Configuration

The current configuration in `training/cfg/train.yaml` is:

```yaml
env:
  num_envs: 20
  max_episode_length: 2000
  env_spacing: 4.0
  num_obstacles: 120
env_dyn:
  num_obstacles: 32
  vel_range: [0.3, 0.5]
  local_range: [4.0, 4.0, 3.0]
```

This configuration should be treated as the current training stage, not as a fully validated final benchmark. The most clearly validated milestone result in the experiment history is the `120 static + 32 dynamic` setup with `vel_range=[0.2, 0.4]` and `local_range=[3.0, 3.0, 3.0]`, which reached about `70%` pass rate.

## Technical Contribution Boundary

To present this project honestly in a resume or interview, the contribution boundary should be stated clearly.

### My Direct Contributions

I directly worked on:

- environment reset logic for obstacle-field crossing
- reward shaping for stability and smoother avoidance behavior
- dynamic obstacle spawn constraints near start/goal corridors
- configuration design for staged curriculum learning
- training/debugging loop refinement and replay workflow stabilization
- repeated experiment analysis based on replay behavior and failure patterns

### What Was Already Provided by the Upstream Project

The following major components were already available in the upstream NavRL/OmniDrones stack:

- base PPO training framework
- core policy network structure
- Isaac Sim training environment scaffolding
- velocity controller and Lee position controller
- general robot/simulator integration

### What This Project Does Not Claim

This project does **not** claim:

- inventing a new RL algorithm
- redesigning the full NavRL architecture from scratch
- completing real-world deployment on a physical UAV
- proving state-of-the-art performance against a formal benchmark suite

A fair and accurate description is:

> Built a practical Isaac-Sim-based UAV dynamic-obstacle navigation training workflow on top of the NavRL framework, and improved mixed static/dynamic navigation performance through environment design, reward shaping, and staged curriculum tuning.

## Project Structure

Key files for this project showcase:

- `training/scripts/env.py`
  - environment generation
  - reset logic
  - observation construction
  - reward calculation
  - collision detection
- `training/scripts/train.py`
  - PPO training entry point
  - checkpoint resume logic
  - training summary output
- `training/scripts/eval.py`
  - replay / evaluation entry point
- `training/cfg/train.yaml`
  - experiment configuration
- `train.sh`
  - local training launcher
- `back.sh`
  - local replay launcher

## How to Run

### Train

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/train.sh
```

### Replay

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/back.sh
```

### Example Evaluation Commands

Static only:

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/back.sh env.num_obstacles=120 env_dyn.num_obstacles=0
```

Mixed static + dynamic:

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/back.sh env.num_obstacles=120 env_dyn.num_obstacles=32 env_dyn.vel_range='[0.2,0.4]' env_dyn.local_range='[3.0,3.0,3.0]'
```

Current stronger dynamic setting:

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/back.sh env.num_obstacles=120 env_dyn.num_obstacles=32 env_dyn.vel_range='[0.3,0.5]' env_dyn.local_range='[4.0,4.0,3.0]'
```

## Resume-Friendly Description

A concise version suitable for a resume:

> Developed an Isaac-Sim-based quadrotor reinforcement learning navigation pipeline on top of NavRL, and improved mixed static/dynamic obstacle traversal by modifying reset logic, reward shaping, and obstacle generation constraints. Achieved about `70%` pass rate in a scene with `120` static and `32` dynamic obstacles.

## Suggested Visualization Materials

To make this project interview-ready, prepare the following assets.

### A. Demo Videos

Recommended filenames:

- `media/static_120_success.mp4`
- `media/dynamic_120_16_failure_analysis.mp4`
- `media/dynamic_120_32_success.mp4`
- `media/post_avoidance_stability_before_after.mp4`
- `media/current_config_120_32_v035_05_local443.mp4`

What each video should show:

- `static_120_success.mp4`
  - successful traversal in pure static scene
- `dynamic_120_16_failure_analysis.mp4`
  - representative failure where the first avoidance succeeds but posture becomes unstable afterward
- `dynamic_120_32_success.mp4`
  - successful traversal in the validated `120 + 32` mixed scene
- `post_avoidance_stability_before_after.mp4`
  - side-by-side comparison before vs. after adding angular/throttle penalties
- `current_config_120_32_v035_05_local443.mp4`
  - current training-stage behavior under the stronger dynamic setting

### B. Figures for README / Portfolio / PPT

Recommended figure list:

- `figures/result_table.png`
  - one-page summarized result table
- `figures/curriculum_schedule.png`
  - progression from static -> 8 dynamic -> 16 dynamic -> 32 dynamic
- `figures/failure_modes.png`
  - examples of diagonal escape, static collision after dynamic disturbance, and post-avoidance wobble
- `figures/system_pipeline.png`
  - observation -> PPO -> controller -> simulator diagram

### C. What to Record During Replay

During replay, try to capture:

- a full successful run
- one representative failed run
- one comparison clip before and after the stability reward changes
- one clip showing that the drone no longer escapes diagonally around the map boundary

### D. Minimal Portfolio Package

If time is limited, prepare at least:

- 1 README screenshot
- 1 result table image
- 1 successful mixed-scene video
- 1 failure-analysis video

That is already enough for resume attachment, interview discussion, or a portfolio page.

## Interview Talking Points

If this project is used in interviews, emphasize the following:

- the challenge was not only training a policy, but making the training loop reliable enough for repeated experiments
- many failures in dynamic scenes were actually caused by posture instability and then ended as static collisions
- the key improvements came from environment design, reward shaping, and staged curriculum learning rather than blindly changing the neural network

## Future Work

Useful next steps if this project continues:

- add a small ablation study for angular/throttle penalties
- export replay videos and result figures into a `media/` folder
- test stronger dynamic settings such as larger `local_range` or higher `vel_range`
- add sim-to-real-oriented noise/randomization for deployment readiness
- organize a one-page benchmark sheet for interview use
