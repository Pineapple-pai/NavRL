import argparse
import csv
import glob
import importlib.util
import json
import os
import sys
import traceback
from statistics import mean

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


def set_policy_eval_mode(policy):
    for module_name in ("feature_extractor", "actor", "critic", "value_norm"):
        module = getattr(policy, module_name, None)
        if module is not None:
            module.eval()


def extract_episode_stats(trajs, goal_hold_steps: int = 5):
    done = trajs.get(("next", "done")).cpu().squeeze(-1)
    terminated = trajs.get(("next", "terminated")).cpu().squeeze(-1)
    truncated = trajs.get(("next", "truncated")).cpu().squeeze(-1)
    reach_goal = trajs[("next", "stats", "reach_goal")].cpu().bool().squeeze(-1)

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

    goal_hold_steps = max(int(goal_hold_steps), 1)
    if reach_goal.shape[1] >= goal_hold_steps:
        stable_goal_windows = reach_goal.float().unfold(1, goal_hold_steps, 1).sum(dim=-1) >= goal_hold_steps
        stable_goal_end_limit = torch.clamp(first_done - goal_hold_steps + 1, min=-1)
        stable_time_index = torch.arange(stable_goal_windows.shape[1]).unsqueeze(0)
        stable_goal_mask = stable_time_index <= stable_goal_end_limit[:, None]
        stable_goal_reached = (stable_goal_windows & stable_goal_mask).any(dim=1)
    else:
        stable_goal_reached = torch.zeros_like(reached_goal_in_episode)

    def take_first_episode(tensor: torch.Tensor):
        indices = first_done.to(tensor.device)
        indices = indices.reshape(indices.shape + (1,) * (tensor.ndim - 1))
        return torch.take_along_dim(tensor, indices, dim=1).reshape(-1)

    traj_stats = {
        k: take_first_episode(v).float().cpu()
        for k, v in trajs[("next", "stats")].items()
    }
    stats = {
        k: float(v.mean().item())
        for k, v in traj_stats.items()
    }
    stats["showcase_pass"] = float((reached_goal_in_episode | (truncated_at_end & ~terminated_at_end)).float().mean().item())
    stats["evaluation_success"] = float((stable_goal_reached & ~terminated_at_end).float().mean().item())
    stats["goal_contact"] = float(reached_goal_in_episode.float().mean().item())
    return stats


def write_outputs(output_dir: str, case_name: str, checkpoint_path: str, overrides: list[str], rows: list[dict]):
    os.makedirs(output_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, f"{case_name}_by_seed.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "seed",
                "return",
                "episode_len",
                "reach_goal",
                "goal_contact",
                "showcase_pass",
                "evaluation_success",
                "collision",
                "truncated",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "case_name": case_name,
        "checkpoint": checkpoint_path,
        "overrides": overrides,
        "num_seeds": len(rows),
        "return_mean": mean(row["return"] for row in rows),
        "episode_len_mean": mean(row["episode_len"] for row in rows),
        "reach_goal_rate": mean(row["reach_goal"] for row in rows),
        "goal_contact_rate": mean(row["goal_contact"] for row in rows),
        "showcase_pass_rate": mean(row["showcase_pass"] for row in rows),
        "evaluation_success_rate": mean(row["evaluation_success"] for row in rows),
        "collision_rate": mean(row["collision"] for row in rows),
        "truncated_rate": mean(row["truncated"] for row in rows),
    }

    json_path = os.path.join(output_dir, f"{case_name}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(output_dir, f"{case_name}_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {case_name} 评估结果\n\n")
        f.write(f"- checkpoint: `{checkpoint_path}`\n")
        f.write(f"- num_seeds: `{len(rows)}`\n")
        f.write(f"- overrides: `{ ' '.join(overrides) if overrides else '(none)' }`\n\n")
        f.write(f"- showcase pass 定义：`第一回合内曾接近目标，或未碰撞并以 truncated 结束`\n")
        f.write(f"- evaluation success 定义：`第一回合内连续 {summary.get('goal_hold_steps', 5)} 步进入目标区，且回合最终不是 terminated`\n\n")
        f.write("- 统计范围说明：`本文件是多 seed 汇总结果；PNG/MP4 通常只对应单个 seed 的一次 20 环境展示回放，因此数值不一定与本表完全相等。`\n\n")
        f.write("| 指标 | 数值 |\n")
        f.write("| --- | --- |\n")
        f.write(f"| 平均回报 | `{summary['return_mean']:.4f}` |\n")
        f.write(f"| 平均回合长度 | `{summary['episode_len_mean']:.4f}` |\n")
        f.write(f"| 原始 reach_goal 率 | `{summary['reach_goal_rate']:.4f}` |\n")
        f.write(f"| 目标区接触率 | `{summary['goal_contact_rate']:.4f}` |\n")
        f.write(f"| 展示通过率（showcase pass） | `{summary['showcase_pass_rate']:.4f}` |\n")
        f.write(f"| 正式成功率（evaluation success） | `{summary['evaluation_success_rate']:.4f}` |\n")
        f.write(f"| 碰撞率 | `{summary['collision_rate']:.4f}` |\n")
        f.write(f"| 截断率 | `{summary['truncated_rate']:.4f}` |\n")

    return csv_path, json_path, md_path, summary


def write_partial_outputs(output_dir: str, case_name: str, checkpoint_path: str, overrides: list[str], rows: list[dict]):
    if not rows:
        return None
    return write_outputs(output_dir, case_name, checkpoint_path, overrides, rows)


def append_debug_log(output_dir: str, case_name: str, message: str):
    os.makedirs(output_dir, exist_ok=True)
    debug_path = os.path.join(output_dir, f"{case_name}_debug.log")
    with open(debug_path, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def log(output_dir: str, case_name: str, message: str):
    print(message, flush=True)
    append_debug_log(output_dir, case_name, message)


def main():
    parser = argparse.ArgumentParser(description="Evaluate NavRL policy statistics across multiple seeds.")
    parser.add_argument("--case-name", required=True, help="Case identifier used for output filenames")
    parser.add_argument("--output-dir", required=True, help="Directory to store evaluation results")
    parser.add_argument("--checkpoint", default=None, help="Checkpoint path; defaults to latest checkpoint_*.pt")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4], help="Seed list")
    parser.add_argument("--num-envs", type=int, default=20, help="Parallel environments used per evaluation seed")
    parser.add_argument("--max-steps", type=int, default=None, help="Max steps per episode; defaults to env.max_episode_length")
    parser.add_argument("--goal-hold-steps", type=int, default=5, help="Consecutive goal-contact steps required for evaluation success")
    args, overrides = parser.parse_known_args()

    os.makedirs(args.output_dir, exist_ok=True)
    debug_path = os.path.join(args.output_dir, f"{args.case_name}_debug.log")
    if os.path.exists(debug_path):
        os.remove(debug_path)

    cfg = load_cfg(overrides)
    cfg.headless = True
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

    checkpoint_path = resolve_checkpoint(args.checkpoint)
    log(args.output_dir, args.case_name, f"[NavRL][Stats]: loading checkpoint {checkpoint_path}")
    log(args.output_dir, args.case_name, f"[NavRL][Stats]: seeds={args.seeds}, num_envs={args.num_envs}")

    sim_app = SimulationApp({"headless": cfg.headless, "anti_aliasing": 0})

    from env import NavigationEnv
    from ppo import PPO
    from omni_drones.controllers import LeePositionController
    from omni_drones.utils.torchrl.transforms import VelController
    from torchrl.envs.transforms import Compose, TransformedEnv
    from torchrl.envs.utils import ExplorationType, set_exploration_type

    env = NavigationEnv(cfg)
    log(args.output_dir, args.case_name, "[NavRL][Stats]: environment initialized")
    controller = LeePositionController(9.81, env.drone.params).to(cfg.device)
    vel_transform = VelController(controller, yaw_control=False)
    transformed_env = TransformedEnv(env, Compose(vel_transform)).train()

    policy = PPO(cfg.algo, transformed_env.observation_spec, transformed_env.action_spec, cfg.device)
    policy.load_state_dict(torch.load(checkpoint_path))
    set_policy_eval_mode(policy)
    log(args.output_dir, args.case_name, "[NavRL][Stats]: policy loaded")

    rows = []
    try:
        env.enable_render(False)
        env.eval()

        for seed in args.seeds:
            transformed_env.set_seed(seed)
            env.set_seed(seed)
            log(args.output_dir, args.case_name, f"[NavRL][Stats]: starting seed {seed}")
            with set_exploration_type(ExplorationType.MEAN):
                trajs = transformed_env.rollout(
                    max_steps=cfg.env.max_episode_length,
                    policy=policy,
                    auto_reset=True,
                    break_when_any_done=False,
                    return_contiguous=False,
                )
            log(args.output_dir, args.case_name, f"[NavRL][Stats]: rollout finished for seed {seed}")
            stats = extract_episode_stats(trajs, goal_hold_steps=args.goal_hold_steps)
            row = {
                "seed": seed,
                "return": stats.get("return", 0.0),
                "episode_len": stats.get("episode_len", 0.0),
                "reach_goal": stats.get("reach_goal", 0.0),
                "goal_contact": stats.get("goal_contact", 0.0),
                "showcase_pass": stats.get("showcase_pass", 0.0),
                "evaluation_success": stats.get("evaluation_success", 0.0),
                "collision": stats.get("collision", 0.0),
                "truncated": stats.get("truncated", 0.0),
            }
            rows.append(row)
            log(
                args.output_dir,
                args.case_name,
                f"[NavRL][Stats][seed={seed}] "
                f"reach={row['reach_goal']:.4f}, goal_contact={row['goal_contact']:.4f}, showcase_pass={row['showcase_pass']:.4f}, "
                f"evaluation_success={row['evaluation_success']:.4f}, collision={row['collision']:.4f}, truncated={row['truncated']:.4f}, return={row['return']:.4f}"
            )
            write_partial_outputs(
                args.output_dir,
                args.case_name,
                checkpoint_path,
                overrides,
                rows,
            )
            env.reset()

        csv_path, json_path, md_path, summary = write_outputs(
            args.output_dir,
            args.case_name,
            checkpoint_path,
            overrides,
            rows,
        )
        summary["goal_hold_steps"] = args.goal_hold_steps
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {args.case_name} 评估结果\n\n")
            f.write(f"- checkpoint: `{checkpoint_path}`\n")
            f.write(f"- num_seeds: `{len(rows)}`\n")
            f.write(f"- overrides: `{ ' '.join(overrides) if overrides else '(none)' }`\n\n")
            f.write(f"- showcase pass 定义：`第一回合内曾接近目标，或未碰撞并以 truncated 结束`\n")
            f.write(f"- evaluation success 定义：`第一回合内连续 {args.goal_hold_steps} 步进入目标区，且回合最终不是 terminated`\n\n")
            f.write("- 统计范围说明：`本文件是多 seed 汇总结果；PNG/MP4 通常只对应单个 seed 的一次 20 环境展示回放，因此数值不一定与本表完全相等。`\n\n")
            f.write("| 指标 | 数值 |\n")
            f.write("| --- | --- |\n")
            f.write(f"| 平均回报 | `{summary['return_mean']:.4f}` |\n")
            f.write(f"| 平均回合长度 | `{summary['episode_len_mean']:.4f}` |\n")
            f.write(f"| 原始 reach_goal 率 | `{summary['reach_goal_rate']:.4f}` |\n")
            f.write(f"| 目标区接触率 | `{summary['goal_contact_rate']:.4f}` |\n")
            f.write(f"| 展示通过率（showcase pass） | `{summary['showcase_pass_rate']:.4f}` |\n")
            f.write(f"| 正式成功率（evaluation success） | `{summary['evaluation_success_rate']:.4f}` |\n")
            f.write(f"| 碰撞率 | `{summary['collision_rate']:.4f}` |\n")
            f.write(f"| 截断率 | `{summary['truncated_rate']:.4f}` |\n")
        log(args.output_dir, args.case_name, "[NavRL][Stats]: summary")
        log(
            args.output_dir,
            args.case_name,
            f"  reach_goal_rate={summary['reach_goal_rate']:.4f}, showcase_pass_rate={summary['showcase_pass_rate']:.4f}, "
            f"evaluation_success_rate={summary['evaluation_success_rate']:.4f}, collision_rate={summary['collision_rate']:.4f}, "
            f"truncated_rate={summary['truncated_rate']:.4f}, return_mean={summary['return_mean']:.4f}"
        )
        log(args.output_dir, args.case_name, f"[NavRL][Stats]: wrote {csv_path}")
        log(args.output_dir, args.case_name, f"[NavRL][Stats]: wrote {json_path}")
        log(args.output_dir, args.case_name, f"[NavRL][Stats]: wrote {md_path}")
    except Exception as exc:
        log(args.output_dir, args.case_name, f"[NavRL][Stats][ERROR]: {type(exc).__name__}: {exc}")
        log(args.output_dir, args.case_name, traceback.format_exc())
        write_partial_outputs(
            args.output_dir,
            args.case_name,
            checkpoint_path,
            overrides,
            rows,
        )
        raise
    finally:
        try:
            env.reset()
        except Exception:
            pass
        sim_app.close()


if __name__ == "__main__":
    main()
