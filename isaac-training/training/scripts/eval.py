import argparse
import os
import sys
import importlib.util
import hydra
import datetime
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

    import glob
    checkpoint_candidates = glob.glob("/home/p/NavRL_checkpoints/checkpoint_*.pt")
    if not checkpoint_candidates:
        raise FileNotFoundError("No checkpoint_*.pt found in /home/p/NavRL_checkpoints. Please train first.")
    checkpoint = max(checkpoint_candidates, key=os.path.getmtime)
    print(f"[NavRL]: Loading checkpoint: {checkpoint}")
    policy.load_state_dict(torch.load(checkpoint))
    
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
    for i, data in enumerate(collector):
        # print("data: ", data)
        # print("============================")
        # Log Info
        info = {"env_frames": collector._frames, "rollout_fps": collector._fps}

        # # Train Policy
        # train_loss_stats = policy.train(data)
        # info.update(train_loss_stats) # log training loss info

        # # Calculate and log training episode stats
        # episode_stats.add(data)
        # if len(episode_stats) >= transformed_env.num_envs: # evaluate once if all agents finished one episode
        #     stats = {
        #         "train/" + (".".join(k) if isinstance(k, tuple) else k): torch.mean(v.float()).item() 
        #         for k, v in episode_stats.pop().items(True, True)
        #     }
        #     info.update(stats)

        # Evaluate policy and log info
        # if i % cfg.eval_interval == 0:
        print("[NavRL]: start evaluating policy at training step: ", i)
        env.eval()
        eval_info = evaluate(
            env=transformed_env, 
            policy=policy,
            seed=cfg.seed, 
            cfg=cfg,
            exploration_type=ExplorationType.MEAN
        )
        env.train()
        env.reset()
        info.update(eval_info)
        print("\n[NavRL]: evaluation done.")
        
        # Update wand info
        run.log(info)


        # # Save Model
        # if i % cfg.save_interval == 0:
        #     ckpt_path = os.path.join(run.dir, f"checkpoint_{i}.pt")
        #     torch.save(policy.state_dict(), ckpt_path)
        #     print("[NavRL]: model saved at training step: ", i)

    # ckpt_path = os.path.join(run.dir, "checkpoint_final.pt")
    # torch.save(policy.state_dict(), ckpt_path)
    wandb.finish()
    # Keep window open for manual inspection
    print("\n[NavRL]: 回放完成，窗口保持打开。手动关闭窗口以退出。")
    while sim_app.is_running():
        sim_app.update()

if __name__ == "__main__":
    main()
    