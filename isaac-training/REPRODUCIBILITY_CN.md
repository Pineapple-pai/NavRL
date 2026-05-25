# NavRL 项目可复现说明

## 1. 运行环境

- 操作系统：Linux
- Python 环境：Conda 环境 `NavRL`
- 仿真平台：Isaac Sim 4.x
- 主要依赖：PyTorch、TorchRL、OpenCV
- checkpoint 默认目录：`/home/p/NavRL_checkpoints`

## 2. 推荐硬件

- NVIDIA GPU
- 支持图形渲染的桌面环境
- 足够的显存与磁盘空间用于 Isaac Sim 回放和视频导出

## 3. 基础准备

在项目根目录执行：

```bash
bash setup.sh
```

如需手动激活环境：

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate NavRL
```

## 4. checkpoint 来源

评估与回放脚本默认会自动读取：

```bash
/home/p/NavRL_checkpoints/checkpoint_*.pt
```

默认使用该目录下最新的 checkpoint。

如果你想固定模型，可以在底层脚本中传入：

```bash
--checkpoint /path/to/checkpoint_xxx.pt
```

## 5. 一键复现入口

项目根目录提供：

```bash
bash reproduce_project_assets.sh all
```

该命令会完成：

- 4 个主展示场景的视频与截图导出
- 4 个主展示场景的批量统计评估

## 6. 单独复现主展示视频

```bash
bash reproduce_project_assets.sh videos
```

默认参数：

- `VIDEO_STEPS=800`
- `VIDEO_SEED=0`

如需覆盖：

```bash
VIDEO_STEPS=1000 VIDEO_SEED=1 bash reproduce_project_assets.sh videos
```

## 7. 单独复现统计结果

```bash
bash reproduce_project_assets.sh stats
```

默认参数：

- `EVAL_SEEDS="0 1 2 3 4"`
- `GOAL_HOLD_STEPS=5`

如需覆盖：

```bash
EVAL_SEEDS="0 1 2 3 4 5 6 7 8 9" GOAL_HOLD_STEPS=5 bash reproduce_project_assets.sh stats
```

## 8. 主展示素材输出位置

```bash
media/
```

主要包括：

- `static_120_baseline.mp4`
- `dynamic_120_16_medium_density.mp4`
- `dynamic_100_32_stress_test.mp4`
- `dynamic_120_32_high_density_mixed.mp4`
- 对应 4 张 `png`

## 9. 统计结果输出位置

```bash
media/results/
```

主要包括：

- `*_by_seed.csv`
- `*_summary.json`
- `*_summary.md`
- `*_debug.log`

## 10. 指标说明

当前项目区分两套指标：

- `showcase pass`
  - 用于 PNG 和视频展示
  - 更适合表达“这一批 20 架无人机展示出来的通过表现”

- `evaluation success`
  - 用于正式评估
  - 定义为：第一回合中连续若干步进入目标区，且回合最终不是 `terminated`

## 11. 推荐复现顺序

建议按以下顺序进行：

- 先执行 `bash reproduce_project_assets.sh videos`
- 再执行 `bash reproduce_project_assets.sh stats`
- 最后查看 `media/` 与 `media/results/` 中的输出文件

## 12. 典型展示用途

- `media/*.mp4` 与 `media/*.png` 适合放在 README、作品集、面试展示中
- `media/results/*.md` 适合放在答辩材料、实验汇总和项目报告中
