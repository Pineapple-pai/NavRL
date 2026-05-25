import argparse
import importlib.util
import os
import sys
import hydra
import datetime
import time
import wandb
import torch
from omegaconf import DictConfig, OmegaConf

try:
    from isaacsim import SimulationApp
except Exception:
    from omni.isaac.kit import SimulationApp




FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cfg")
@hydra.main(config_path=FILE_PATH, config_name="train", version_base=None)
def main(cfg):
    script_root = os.path.abspath(os.path.dirname(__file__))
    if script_root not in sys.path:
        sys.path.insert(0, script_root)

    def _get_metric(info, *keys):
        for key in keys:
            if key in info:
                value = info[key]
                if isinstance(value, torch.Tensor):
                    value = value.detach().float().mean().item()
                return float(value)
        return None

    def _fmt_metric(value, precision=3):
        if value is None:
            return "n/a"
        return f"{value:.{precision}f}"

    def _fmt_duration(seconds):
        if seconds is None:
            return "n/a"
        seconds = max(int(seconds), 0)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

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

    # Simulation App
    sim_app = SimulationApp({"headless": cfg.headless, "anti_aliasing": 1})

    local_utils_path = os.path.join(script_root, "utils.py")
    if os.path.exists(local_utils_path):
        utils_spec = importlib.util.spec_from_file_location("utils", local_utils_path)
        if utils_spec is not None and utils_spec.loader is not None:
            utils_module = importlib.util.module_from_spec(utils_spec)
            utils_spec.loader.exec_module(utils_module)
            sys.modules["utils"] = utils_module

    from ppo import PPO
    from omni_drones.controllers import LeePositionController
    from omni_drones.utils.torchrl.transforms import VelController
    from omni_drones.utils.torchrl import SyncDataCollector, EpisodeStats
    from torchrl.envs.transforms import TransformedEnv, Compose
    from utils import evaluate
    from torchrl.envs.utils import ExplorationType

    # Use Wandb to monitor training
    if (cfg.wandb.run_id is None):
        run = wandb.init(
            project=cfg.wandb.project,
            name=f"{cfg.wandb.name}/{datetime.datetime.now().strftime('%m-%d_%H-%M')}",
            entity=cfg.wandb.entity,
            config=OmegaConf.to_container(cfg, resolve=True),
            mode=cfg.wandb.mode,
            id=wandb.util.generate_id(),
        )
    else:
        run = wandb.init(
            project=cfg.wandb.project,
            name=f"{cfg.wandb.name}/{datetime.datetime.now().strftime('%m-%d_%H-%M')}",
            entity=cfg.wandb.entity,
            config=OmegaConf.to_container(cfg, resolve=True),
            mode=cfg.wandb.mode,
            id=cfg.wandb.run_id,
            resume="must"
        )

    # Navigation Training Environment
    from env import NavigationEnv
    env = NavigationEnv(cfg)

    # Transformed Environment
    transforms = []
    # transforms.append(ravel_composite(env.observation_spec, ("agents", "intrinsics"), start_dim=-1))
    controller = LeePositionController(9.81, env.drone.params).to(cfg.device)
    vel_transform = VelController(controller, yaw_control=False)
    transforms.append(vel_transform)
    transformed_env = TransformedEnv(env, Compose(*transforms)).train()
    transformed_env.set_seed(cfg.seed)    
    # PPO Policy
    policy = PPO(cfg.algo, transformed_env.observation_spec, transformed_env.action_spec, cfg.device)

    # Auto-load latest checkpoint if exists for resume training
    ckpt_dir = "/home/p/NavRL_checkpoints"
    start_step = 0
    if os.path.exists(ckpt_dir):
        ckpt_files = []
        for f in os.listdir(ckpt_dir):
            if not (f.startswith("checkpoint_") and f.endswith(".pt")):
                continue
            step_str = f[len("checkpoint_"):-len(".pt")]
            if not step_str.isdigit():
                continue
            ckpt_files.append((int(step_str), f))
        if ckpt_files:
            ckpt_files.sort(key=lambda item: item[0])
            start_step, latest_ckpt = ckpt_files[-1]
            checkpoint_path = os.path.join(ckpt_dir, latest_ckpt)
            print(f"[NavRL]: Loading checkpoint from {checkpoint_path}")
            policy.load_state_dict(torch.load(checkpoint_path))
            print(f"[NavRL]: Resuming training from step {start_step}")
        else:
            print("[NavRL]: No checkpoint found, starting from scratch")
    else:
        print("[NavRL]: Checkpoint directory not found, starting from scratch")
    
    # Episode Stats Collector
    episode_stats_keys = [
        k for k in transformed_env.observation_spec.keys(True, True) 
        if isinstance(k, tuple) and k[0]=="stats"
    ]
    episode_stats = EpisodeStats(episode_stats_keys)

    # RL Data Collector
    collector = SyncDataCollector(
        transformed_env,
        policy=policy, 
        frames_per_batch=cfg.env.num_envs * cfg.algo.training_frame_num, 
        total_frames=cfg.max_frame_num,
        device=cfg.device,
        return_same_td=True, # update the return tensordict inplace (should set to false if we need to use replace buffer)
        exploration_type=ExplorationType.RANDOM, # sample from normal distribution
    )

    # Training Loop
    last_ckpt_path = None
    train_start_time = time.time()
    # Running counters for termination stats
    _total_episodes = 0
    _total_reach = 0
    _total_collision = 0
    _total_truncated = 0
    _total_return = 0.0
    _total_ep_len = 0
    _window_episodes = 0
    _window_reach = 0
    _window_collision = 0
    _window_truncated = 0
    _window_return = 0.0
    _window_ep_len = 0
    for i, data in enumerate(collector):
        step = i + start_step  # Actual step number including resumed training
        # print("data: ", data)
        # print("============================")
        # Log Info
        info = {"env_frames": collector._frames + (start_step * cfg.env.num_envs * cfg.algo.training_frame_num), "rollout_fps": collector._fps}

        # Train Policy
        train_loss_stats = policy.train(data)
        info.update(train_loss_stats) # log training loss info

        # Calculate and log training episode stats
        episode_stats.add(data)
        if len(episode_stats) >= transformed_env.num_envs: # evaluate once if all agents finished one episode
            stats = {
                "train/" + (".".join(k) if isinstance(k, tuple) else k): torch.mean(v.float()).item() 
                for k, v in episode_stats.pop().items(True, True)
            }
            info.update(stats)

        # Evaluate policy and log info
        if (step % cfg.eval_interval == 0) and (not cfg.headless):
            print(f"[NavRL]: start evaluating policy at training step: {step}")
            env.enable_render(True)
            env.eval()
            eval_info = evaluate(
                env=transformed_env, 
                policy=policy,
                seed=cfg.seed, 
                cfg=cfg,
                exploration_type=ExplorationType.MEAN
            )
            env.enable_render(not cfg.headless)
            env.train()
            env.reset()
            info.update(eval_info)
            print("\n[NavRL]: evaluation done.")
        
        # Update wand info
        run.log(info)

        if step == 0 or step % 50 == 0 or step % cfg.save_interval == 0:
            # Accumulate per-step termination stats into running counters
            try:
                raw_stats = env.stats
                step_terminated = (raw_stats["reach_goal"].bool() | raw_stats["collision"].bool() | raw_stats["truncated"].bool()).sum().item()
                step_reach = raw_stats["reach_goal"].bool().sum().item()
                step_collision = raw_stats["collision"].bool().sum().item()
                step_truncated = raw_stats["truncated"].bool().sum().item()
                _total_episodes += step_terminated
                _total_reach += step_reach
                _total_collision += step_collision
                _total_truncated += step_truncated
                _window_episodes += step_terminated
                _window_reach += step_reach
                _window_collision += step_collision
                _window_truncated += step_truncated
                # Use recent window (last 50 steps) for display
                if _window_episodes > 0:
                    reach_goal = _window_reach / _window_episodes
                    collision = _window_collision / _window_episodes
                    truncated = _window_truncated / _window_episodes
                else:
                    reach_goal = collision = truncated = None
                train_return = raw_stats["return"].float().mean().item()
                episode_len = raw_stats["episode_len"].float().mean().item()
            except Exception:
                train_return = reach_goal = collision = truncated = episode_len = None
            # Reset window every 500 steps
            if step % 500 == 0 and step > 0:
                _window_episodes = 0
                _window_reach = 0
                _window_collision = 0
                _window_truncated = 0
            actor_loss = _get_metric(info, "actor_loss", "loss_actor", "train/actor_loss")
            critic_loss = _get_metric(info, "critic_loss", "loss_critic", "train/critic_loss")
            env_frames = int(info["env_frames"])
            total_frames = int(cfg.max_frame_num)
            progress = 100.0 * env_frames / max(total_frames, 1)
            elapsed_seconds = time.time() - train_start_time
            fps_value = _get_metric(info, "rollout_fps")
            frames_per_step = cfg.env.num_envs * cfg.algo.training_frame_num
            if fps_value is not None and fps_value > 0:
                eta_seconds = max(total_frames - env_frames, 0) / fps_value
            else:
                eta_seconds = None
            print("[NavRL][训练摘要]------------------------------")
            print(
                f"进度: 第 {step} 步 | {env_frames}/{total_frames} 帧 | 完成 {progress:.2f}%"
            )
            print(
                f"速度: {frames_per_step} 帧/步 | { _fmt_metric(fps_value, 1) } 帧/秒 | 已训练 { _fmt_duration(elapsed_seconds) } | 预计剩余 { _fmt_duration(eta_seconds) }"
            )
            print(
                f"效果: 平均回报={_fmt_metric(train_return)} | 到达率={_fmt_metric(reach_goal)} | 碰撞率={_fmt_metric(collision)} | 截断率={_fmt_metric(truncated)}"
            )
            print(
                f"状态: 平均回合长度={_fmt_metric(episode_len, 1)} | ActorLoss={_fmt_metric(actor_loss)} | CriticLoss={_fmt_metric(critic_loss)}"
            )
            if last_ckpt_path is not None:
                print(f"存档: {last_ckpt_path}")
            print("[NavRL][训练摘要]------------------------------")


        # Save Model
        if step % cfg.save_interval == 0:
            ckpt_dir = "/home/p/NavRL_checkpoints"
            os.makedirs(ckpt_dir, exist_ok=True)
            ckpt_path = os.path.join(ckpt_dir, f"checkpoint_{step}.pt")
            torch.save(policy.state_dict(), ckpt_path)
            last_ckpt_path = ckpt_path
            print(f"[NavRL]: model saved at training step: {step}")

    ckpt_dir = "/home/p/NavRL_checkpoints"
    os.makedirs(ckpt_dir, exist_ok=True)
    ckpt_path = os.path.join(ckpt_dir, "checkpoint_final.pt")
    torch.save(policy.state_dict(), ckpt_path)
    wandb.finish()
    sim_app.close()

if __name__ == "__main__":
    main()
    