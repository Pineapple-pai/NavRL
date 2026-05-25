# NavRL Isaac Training 项目说明（中文版）

## 项目概述

本子项目基于 `NavRL`、`Isaac Sim 4.x` 和 `PPO`，实现了一个面向四旋翼无人机的强化学习导航训练流程，目标是在混合静态障碍与动态障碍环境中完成稳定穿越。

这项工作的重点不是重新设计整套 NavRL 算法，而是让 `isaac-training` 这部分在本地环境中真正具备：

- 可持续训练
- 可重复调试
- 可视化回放
- 可量化评估
- 可用于项目展示

## 核心问题

整个项目主要围绕以下四个实际问题展开：

- 减少无人机沿地图边缘对角线逃逸、绕开障碍场的行为
- 在引入动态障碍后尽量保留原有静态避障能力
- 改善首次避障后姿态摇晃、后续连续碰撞的问题
- 提高训练与回放流程的稳定性，支持反复实验和行为分析

## 技术栈

- `Python 3.10`
- `Isaac Sim 4.x`
- `PyTorch`
- `TorchRL`
- `Hydra`
- `OpenCV`
- `NavRL / OmniDrones`

## 任务设置

无人机需要从地图一侧飞到另一侧，在飞行过程中避开：

- 静态障碍物
- 在局部范围内移动的动态障碍物

策略输入主要包括：

- 无人机本体状态
- LiDAR 观测
- 目标方向
- 动态障碍物特征

策略输出为速度目标，再通过：

- `VelController`
- `LeePositionController`

转换为底层控制命令。

## 我做了哪些修改

### 1. 环境与任务定义优化

- 修改重置分布，使无人机更倾向于真正穿越障碍区
- 收窄横向自由度，减少沿边缘绕飞的“捷径”行为
- 对动态障碍生成加入起点 / 终点走廊保护

### 2. 奖励与稳定性改进

- 在原有前进奖励与安全奖励基础上加入姿态稳定性约束
- 增加角速度惩罚与油门变化惩罚
- 缓解首次避障后姿态不稳导致的连续碰撞问题

### 3. 训练与回放工作流优化

- 优化 checkpoint 恢复逻辑
- 改善回放脚本与渲染环境设置
- 支持批量视频导出和批量评估输出

### 4. 结果表达方式改进

- 区分 `showcase pass` 与 `evaluation success`
- 让视频展示指标与正式统计指标分开表达
- 将结果整理为 `csv/json/md` 统一输出

## 当前结果如何理解

项目当前同时保留两类结果：

- **展示材料**
  - `media/*.png`
  - `media/*.mp4`
  - 更适合 README、作品集和汇报展示
- **正式统计文件**
  - `media/results/*.md`
  - `media/results/*.json`
  - `media/results/*.csv`
  - 更适合答辩材料、实验汇总和项目报告引用

需要注意的是：

- `png/mp4` 通常对应单个 `seed` 的一次 20 环境展示回放
- `media/results/*.md` 默认是多 `seed` 汇总后的统计结果
- 两者在 `showcase pass` 定义上相关，但数值**不一定完全相等**

## 当前可直接引用的结果文件

- [`media/results/static_120_summary.md`](media/results/static_120_summary.md)
- [`media/results/dynamic_120_16_summary.md`](media/results/dynamic_120_16_summary.md)
- [`media/results/dynamic_100_32_summary.md`](media/results/dynamic_100_32_summary.md)
- [`media/results/dynamic_120_32_summary.md`](media/results/dynamic_120_32_summary.md)

## 当前可稳妥表述的结论

基于当前仓库中已经整理出的材料，可以较稳妥地表达为：

- 已完成静态、动态和高密度混合障碍场景的批量回放展示
- 已形成多 `seed`、多环境批量评估工作流
- 环境设计、奖励塑形和课程学习对动态场景稳定性有明显影响
- 项目当前已经具备“展示材料 + 统计结果 + 复现脚本”三位一体的工程化展示基础

如果要引用更正式的结果，请优先使用 `media/results/*.md` 中的当前统计值；如果要描述历史实验观察，应明确写成“历史阶段性结果”而不是与当前 summary 直接等同。

## 关键文件

- `training/scripts/env.py`
  - 场景生成、重置逻辑、观测构建、奖励计算
- `training/scripts/train.py`
  - PPO 训练入口、checkpoint 恢复逻辑
- `training/scripts/evaluate_case_stats.py`
  - 多 `seed`、多环境批量统计
- `training/scripts/export_demo_video.py`
  - 导出单次展示回放的 `mp4/png`
- `capture_demo_videos.sh`
  - 批量导出演示素材
- `evaluate_demo_cases.sh`
  - 批量输出统计结果

## 运行方式

### 训练

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/train.sh
```

### 回放

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/back.sh
```

### 批量导出演示素材

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/capture_demo_videos.sh static_120_success
bash /home/p/CascadeProjects/NavRL/isaac-training/capture_demo_videos.sh dynamic_120_16_failure_analysis
bash /home/p/CascadeProjects/NavRL/isaac-training/capture_demo_videos.sh dynamic_100_32_stress
bash /home/p/CascadeProjects/NavRL/isaac-training/capture_demo_videos.sh dynamic_120_32_success
```

### 批量统计结果

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh static_120
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh dynamic_120_16
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh dynamic_100_32
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh dynamic_120_32
```

## 项目边界与结果适用范围

为了保证项目表述准确，建议明确以下边界：

- 本项目基于现有 `NavRL / OmniDrones` 框架开展
- 核心贡献集中在环境设计、奖励塑形、训练流程优化、评估与展示工具链建设
- 当前结果主要在仿真环境中验证，尚未涉及真实无人机实物部署
- 展示图中的 `Pass Rate` 更适合作为 `showcase pass` 解释，不应直接替代正式统计结论

不建议将本项目表述为：

- 从零设计了全新的强化学习算法
- 独立实现了完整无人机控制底层框架
- 已完成真实无人机硬件闭环部署
- 在标准公开 benchmark 上严格证明达到 SOTA

如果需要对外做更稳妥的总结，可以表述为：

> 基于 NavRL 与 Isaac Sim 4.x，对四旋翼无人机动态障碍避障训练流程进行了环境设计、奖励塑形、课程学习与评估展示工具链优化，并在多种静态/动态混合障碍场景中完成了阶段性仿真验证。

## 推荐配套文档

- [`INTERNSHIP_PROJECT_CN.md`](INTERNSHIP_PROJECT_CN.md)
  - 实习 / 面试表达版本
- [`GRADUATION_DESIGN_CN.md`](GRADUATION_DESIGN_CN.md)
  - 毕业设计 / 答辩表达版本
- [`REPRODUCIBILITY_CN.md`](REPRODUCIBILITY_CN.md)
  - 复现实验与素材生成说明
