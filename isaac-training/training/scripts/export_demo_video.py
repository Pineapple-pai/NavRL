import argparse
import glob
import importlib.util
import os
import sys

import cv2
import numpy as np
import torch
from omegaconf import OmegaConf

try:
    from isaacsim import SimulationApp
except Exception:
    from omni.isaac.kit import SimulationApp


CFG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cfg")
DEFAULT_CKPT_DIR = "/home/p/NavRL_checkpoints"


def load_cfg(overrides: list[str]):
    cfg = OmegaConf.merge(
        OmegaConf.load(os.path.join(CFG_DIR, "train.yaml")),
        OmegaConf.load(os.path.join(CFG_DIR, "drone.yaml")),
        OmegaConf.load(os.path.join(CFG_DIR, "ppo.yaml")),
        OmegaConf.load(os.path.join(CFG_DIR, "sim.yaml")),
    )
    if "defaults" in cfg:
        del cfg["defaults"]
    if overrides:
        cfg = OmegaConf.merge(cfg, OmegaConf.from_dotlist(overrides))
    return cfg


def resolve_checkpoint(checkpoint_path: str | None) -> str:
    if checkpoint_path:
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        return checkpoint_path

    checkpoint_candidates = glob.glob(os.path.join(DEFAULT_CKPT_DIR, "checkpoint_*.pt"))
    if not checkpoint_candidates:
        raise FileNotFoundError(
            f"No checkpoint_*.pt found in {DEFAULT_CKPT_DIR}. Please train first or pass --checkpoint."
        )
    return max(checkpoint_candidates, key=os.path.getmtime)


def save_video(frames: np.ndarray, output_path: str, fps: float):
    if frames.ndim != 4 or frames.shape[-1] != 3:
        raise ValueError(f"Unexpected frame shape: {frames.shape}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    height, width = frames.shape[1:3]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not writer.isOpened():
        raise RuntimeError(f"Failed to open video writer for: {output_path}")

    try:
        for frame in frames:
            frame_uint8 = np.asarray(frame, dtype=np.uint8)
            frame_bgr = cv2.cvtColor(frame_uint8, cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)
    finally:
        writer.release()


def extract_episode_summary(trajs):
    done = trajs.get(("next", "done")).cpu().squeeze(-1)
    reach_goal = trajs[("next", "stats", "reach_goal")].cpu().bool().squeeze(-1)
    terminated = trajs.get(("next", "terminated")).cpu().squeeze(-1)
    truncated = trajs.get(("next", "truncated")).cpu().squeeze(-1)

    done_any = done.any(dim=1)
    first_done = torch.argmax(done.long(), dim=1)
    fallback = torch.full_like(first_done, done.shape[1] - 1)
    first_done = torch.where(done_any, first_done, fallback)

    time_index = torch.arange(done.shape[1]).unsqueeze(0)
    first_episode_mask = time_index <= first_done[:, None]

    terminal_indices = first_done[:, None]
    terminated_at_end = torch.take_along_dim(terminated, terminal_indices, dim=1).squeeze(1)
    truncated_at_end = torch.take_along_dim(truncated, terminal_indices, dim=1).squeeze(1)
    reached_goal_in_episode = (reach_goal & first_episode_mask).any(dim=1)
    passed_each = reached_goal_in_episode | (truncated_at_end & ~terminated_at_end)

    passed = int(passed_each.sum().item())
    total = int(passed_each.numel())
    failed = total - passed
    pass_rate = 0.0 if total == 0 else passed / total
    return {
        "passed": passed,
        "failed": failed,
        "total": total,
        "pass_rate": pass_rate,
    }


def annotate_frame(frame_bgr: np.ndarray, summary: dict | None):
    if summary is None:
        return frame_bgr

    annotated = frame_bgr.copy()
    overlay = annotated.copy()
    cv2.rectangle(overlay, (24, 24), (440, 170), (0, 0, 0), -1)
    annotated = cv2.addWeighted(overlay, 0.45, annotated, 0.55, 0)

    lines = [
        f"Total Drones: {summary['total']}",
        f"Passed: {summary['passed']}",
        f"Failed: {summary['failed']}",
        f"Pass Rate: {summary['pass_rate'] * 100:.1f}%",
    ]
    y = 62
    for line in lines:
        cv2.putText(annotated, line, (40, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        y += 28
    return annotated


def save_screenshot(frames: np.ndarray, output_path: str, frame_index: int = -1, summary: dict | None = None):
    if frames.ndim != 4 or frames.shape[-1] != 3:
        raise ValueError(f"Unexpected frame shape: {frames.shape}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    frame = frames[frame_index]
    frame_uint8 = np.asarray(frame, dtype=np.uint8)
    frame_bgr = cv2.cvtColor(frame_uint8, cv2.COLOR_RGB2BGR)
    frame_bgr = annotate_frame(frame_bgr, summary)
    if not cv2.imwrite(output_path, frame_bgr):
        raise RuntimeError(f"Failed to save screenshot to: {output_path}")


def set_policy_eval_mode(policy):
    for module_name in ("feature_extractor", "actor", "critic", "value_norm"):
        module = getattr(policy, module_name, None)
        if module is not None:
            module.eval()


def main():
    parser = argparse.ArgumentParser(description="Export a NavRL replay video to mp4.")
    parser.add_argument("--output", required=True, help="Output mp4 path")
    parser.add_argument("--screenshot-output", default=None, help="Optional PNG path for a representative frame")
    parser.add_argument("--screenshot-frame-index", type=int, default=-1, help="Frame index used when saving screenshot; default is last frame")
    parser.add_argument("--checkpoint", default=None, help="Checkpoint path; defaults to latest checkpoint_*.pt")
    parser.add_argument("--seed", type=int, default=0, help="Random seed for replay")
    parser.add_argument("--frame-interval", type=int, default=2, help="Capture one frame every N simulation steps")
    parser.add_argument("--video-fps", type=float, default=None, help="Override output video fps")
    parser.add_argument("--max-steps", type=int, default=None, help="Max replay steps; defaults to env.max_episode_length")
    parser.add_argument("--num-envs", type=int, default=20, help="Number of environments to render during replay")
    args, overrides = parser.parse_known_args()

    cfg = load_cfg(overrides)
    cfg.headless = False
    cfg.seed = args.seed
    cfg.env.num_envs = args.num_envs
    cfg.wandb.mode = "disabled"
    if args.max_steps is not None:
        cfg.env.max_episode_length = args.max_steps

    script_root = os.path.abspath(os.path.dirname(__file__))
    if script_root not in sys.path:
        sys.path.insert(0, script_root)

    orbit_ext_root = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "third_party",
            "orbit",
            "source",
            "extensions",
            "omni.isaac.orbit",
        )
    )
    if orbit_ext_root not in sys.path:
        sys.path.insert(0, orbit_ext_root)

    local_utils_path = os.path.join(script_root, "utils.py")
    if os.path.exists(local_utils_path):
        utils_spec = importlib.util.spec_from_file_location("utils", local_utils_path)
        if utils_spec is not None and utils_spec.loader is not None:
            utils_module = importlib.util.module_from_spec(utils_spec)
            utils_spec.loader.exec_module(utils_module)
            sys.modules["utils"] = utils_module

    sim_app = SimulationApp({"headless": cfg.headless, "anti_aliasing": 1})

    from env import NavigationEnv
    from ppo import PPO
    from omni_drones.controllers import LeePositionController
    from omni_drones.utils.torchrl.transforms import VelController
    from omni_drones.utils.torchrl.env import RenderCallback
    from torchrl.envs.transforms import Compose, TransformedEnv
    from torchrl.envs.utils import ExplorationType, set_exploration_type

    checkpoint_path = resolve_checkpoint(args.checkpoint)
    print(f"[NavRL][Video]: loading checkpoint {checkpoint_path}")

    env = NavigationEnv(cfg)
    controller = LeePositionController(9.81, env.drone.params).to(cfg.device)
    vel_transform = VelController(controller, yaw_control=False)
    transformed_env = TransformedEnv(env, Compose(vel_transform)).train()
    transformed_env.set_seed(cfg.seed)

    policy = PPO(cfg.algo, transformed_env.observation_spec, transformed_env.action_spec, cfg.device)
    policy.load_state_dict(torch.load(checkpoint_path))
    set_policy_eval_mode(policy)

    env.enable_render(True)
    env.eval()
    env.set_seed(cfg.seed)

    max_steps = cfg.env.max_episode_length
    render_callback = RenderCallback(interval=max(args.frame_interval, 1))

    try:
        with set_exploration_type(ExplorationType.MEAN):
            trajs = transformed_env.rollout(
                max_steps=max_steps,
                policy=policy,
                callback=render_callback,
                auto_reset=True,
                break_when_any_done=False,
                return_contiguous=False,
            )

        frames = render_callback.get_video_array("t h w c")
        if len(frames) == 0:
            raise RuntimeError("No frames were captured during replay.")

        summary = extract_episode_summary(trajs)

        if args.video_fps is not None:
            fps = args.video_fps
        else:
            fps = 1.0 / (args.frame_interval * cfg.sim.dt * cfg.sim.substeps)

        save_video(frames, args.output, fps)
        if args.screenshot_output is not None:
            save_screenshot(frames, args.screenshot_output, args.screenshot_frame_index, summary)
        print(f"[NavRL][Video]: saved {args.output}")
        if args.screenshot_output is not None:
            print(f"[NavRL][Video]: saved {args.screenshot_output}")
        print(
            f"[NavRL][Video]: frames={len(frames)}, fps={fps:.2f}, seed={args.seed}, "
            f"passed={summary['passed']}, failed={summary['failed']}, pass_rate={summary['pass_rate'] * 100:.1f}%"
        )
    finally:
        try:
            env.reset()
        except Exception:
            pass
        sim_app.close()


if __name__ == "__main__":
    main()
