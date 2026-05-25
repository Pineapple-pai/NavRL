# 演示视频生成说明

本目录用于存放 NavRL Isaac Training 项目的演示视频。

注意：本目录中的 `mp4` 文件不是仓库默认自带内容，而是你在本地运行导出脚本成功后才会生成的结果文件。

另外，单个演示视频只能展示一个批量回放片段，**不能直接代表整体通过率**。如果你想展示某个配置的成功率、碰撞率或截断率，请使用批量统计脚本，相关结果会输出到 `media/results/` 目录。

## 已准备好的脚本

- `../capture_demo_videos.sh`
  - 按预设场景导出单个或多个演示视频
- `../training/scripts/export_demo_video.py`
  - 从 Isaac Sim 回放帧直接导出单个 `mp4`
- `../evaluate_demo_cases.sh`
  - 按预设场景批量输出统计结果表
- `../training/scripts/evaluate_case_stats.py`
  - 多 `seed`、多环境统计到达率/碰撞率/截断率

## 推荐生成方式

在 `isaac-training` 目录下运行：

```bash
bash capture_demo_videos.sh static_120_success
bash capture_demo_videos.sh dynamic_120_16_failure_analysis
bash capture_demo_videos.sh dynamic_100_32_stress
bash capture_demo_videos.sh dynamic_120_32_success
```

生成后的视频会默认保存在当前目录下：

- `static_120_baseline.mp4`
- `dynamic_120_16_medium_density.mp4`
- `dynamic_100_32_stress_test.mp4`
- `dynamic_120_32_high_density_mixed.mp4`

更准确地说，这些文件会生成到 `media/` 目录中，例如：

- `media/static_120_baseline.mp4`
- `media/static_120_baseline.png`
- `media/dynamic_120_16_medium_density.mp4`
- `media/dynamic_120_16_medium_density.png`
- `media/dynamic_100_32_stress_test.mp4`
- `media/dynamic_100_32_stress_test.png`
- `media/dynamic_120_32_high_density_mixed.mp4`
- `media/dynamic_120_32_high_density_mixed.png`

当前导出脚本默认会使用 `20` 个环境进行回放，因此视频中会同时出现 `20` 架无人机；对应的 `png` 截图左上角会自动标注：

- `Total Drones`
- `Passed`
- `Failed`
- `Pass Rate`

## 各视频对应含义

### 1. `static_120_baseline.mp4`

场景含义：

- 纯静态障碍环境
- 用于展示无人机在 `120` 个静态障碍下的批量回放基线

命令：

```bash
bash capture_demo_videos.sh static_120_success
```

### 2. `dynamic_120_16_medium_density.mp4`

场景含义：

- `120` 个静态障碍 + `16` 个动态障碍
- 用于展示中等动态密度下的批量回放表现

命令：

```bash
bash capture_demo_videos.sh dynamic_120_16_failure_analysis
```

### 3. `dynamic_100_32_stress_test.mp4`

场景含义：

- `100` 个静态障碍 + `32` 个动态障碍
- 用于展示动态压力测试下的批量回放表现

命令：

```bash
bash capture_demo_videos.sh dynamic_100_32_stress
```

### 4. `dynamic_120_32_high_density_mixed.mp4`

场景含义：

- `120` 个静态障碍 + `32` 个动态障碍
- 用于展示高密度混合场景下的批量回放表现

命令：

```bash
bash capture_demo_videos.sh dynamic_120_32_success
```

## 可选参数

你可以在脚本后面继续追加 Hydra 参数覆盖，例如：

```bash
bash capture_demo_videos.sh static_120_success --seed 1
bash capture_demo_videos.sh dynamic_120_32_success --seed 2
```

或者直接调用底层脚本：

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate NavRL
python training/scripts/export_demo_video.py \
  --output media/custom_demo.mp4 \
  --screenshot-output media/custom_demo.png \
  --seed 0 \
  env.num_obstacles=120 \
  env_dyn.num_obstacles=32 \
  env_dyn.vel_range='[0.2,0.4]' \
  env_dyn.local_range='[3.0,3.0,3.0]' \
  sim.dt=0.05
```

## 注意事项

- 默认会加载 `/home/p/NavRL_checkpoints` 下最新的 `checkpoint_*.pt`
- 如果你想固定某个模型，可以额外传入：

```bash
python training/scripts/export_demo_video.py --output media/demo.mp4 --checkpoint /path/to/checkpoint_12000.pt ...
```

- 建议根据展示需要尝试多个 `seed`，挑选最具有代表性的批量回放画面

## 批量统计结果说明

如果你想表达“这个配置的大致成功率”，推荐运行：

```bash
bash evaluate_demo_cases.sh all
```

或者单独运行某个场景：

```bash
bash evaluate_demo_cases.sh static_120
bash evaluate_demo_cases.sh dynamic_120_16
bash evaluate_demo_cases.sh dynamic_100_32
bash evaluate_demo_cases.sh dynamic_120_32
```

运行后会在 `media/results/` 下生成：

- `*_by_seed.csv`
- `*_summary.json`
- `*_summary.md`

其中：

- `*_by_seed.csv` 适合后续画图
- `*_summary.json` 适合程序读取
- `*_summary.md` 适合直接贴到 README、答辩材料或作品集说明中
