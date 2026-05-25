# NavRL 项目可复现说明

## 1. 运行环境

- 操作系统：Linux
- Python 环境：Conda 环境 `NavRL`
- 仿真平台：Isaac Sim 4.x
- checkpoint 默认目录：`/home/p/NavRL_checkpoints`

## 2. 基础准备

在 `isaac-training` 目录下完成环境准备：

```bash
bash setup.sh
```

如需手动激活环境：

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate NavRL
```

## 3. checkpoint 读取规则

评估与回放脚本默认会自动读取：

```bash
/home/p/NavRL_checkpoints/checkpoint_*.pt
```

默认使用该目录下最新的 checkpoint；如果想固定模型，可在底层脚本中传入：

```bash
--checkpoint /path/to/checkpoint_xxx.pt
```

## 4. 一键复现入口

项目根目录提供：

```bash
bash reproduce_project_assets.sh all
```

该命令会完成：

- 主展示场景的视频与截图导出
- 主展示场景的批量统计评估

## 5. 单独复现展示素材

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

## 6. 单独复现统计结果

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

## 7. 输出位置

### 展示素材

输出到：

```bash
media/
```

主要包括：

- `static_120_baseline.mp4`
- `dynamic_120_16_medium_density.mp4`
- `dynamic_100_32_stress_test.mp4`
- `dynamic_120_32_high_density_mixed.mp4`
- 对应 `png` 截图

### 统计结果

输出到：

```bash
media/results/
```

主要包括：

- `*_by_seed.csv`
- `*_summary.json`
- `*_summary.md`
- `*_debug.log`

## 8. 指标说明

当前项目区分两套指标：

- `showcase pass`
  - 更适合 `PNG` 与视频展示
  - 通常对应单个 `seed` 的 20 环境回放表现
- `evaluation success`
  - 更适合正式评估
  - 定义为：第一回合中连续若干步进入目标区，且回合最终不是 `terminated`

因此：

- `media/*.png` 与 `media/*.mp4` 适合展示
- `media/results/*.md` 更适合正式引用
- 两者统计口径相关，但数值不一定完全相等

## 9. 推荐复现顺序

建议按以下顺序进行：

- 先执行 `bash reproduce_project_assets.sh videos`
- 再执行 `bash reproduce_project_assets.sh stats`
- 最后查看 `media/` 与 `media/results/` 中的输出文件

## 10. 典型使用场景

- `media/*.mp4` 与 `media/*.png` 适合放在 README、作品集、面试展示中
- `media/results/*.md` 适合放在答辩材料、实验汇总和项目报告中

## 11. 展示素材补充说明

当前主展示素材通常包括：

- `media/static_120_baseline.mp4`
- `media/static_120_baseline.png`
- `media/dynamic_120_16_medium_density.mp4`
- `media/dynamic_120_16_medium_density.png`
- `media/dynamic_100_32_stress_test.mp4`
- `media/dynamic_100_32_stress_test.png`
- `media/dynamic_120_32_high_density_mixed.mp4`
- `media/dynamic_120_32_high_density_mixed.png`

推荐生成命令：

```bash
bash capture_demo_videos.sh static_120_success
bash capture_demo_videos.sh dynamic_120_16_failure_analysis
bash capture_demo_videos.sh dynamic_100_32_stress
bash capture_demo_videos.sh dynamic_120_32_success
```

对应场景含义如下：

- `static_120_baseline.mp4`
  - `120` 个静态障碍的批量回放基线
- `dynamic_120_16_medium_density.mp4`
  - `120 + 16` 场景的中等动态密度回放
- `dynamic_100_32_stress_test.mp4`
  - `100 + 32` 场景的动态压力测试回放
- `dynamic_120_32_high_density_mixed.mp4`
  - `120 + 32` 场景的高密度混合回放

如果你想表达“某个配置的大致成功率”，建议优先引用：

- `media/results/*_summary.md`
- 而不是单个 `png/mp4`
