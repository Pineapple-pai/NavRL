# NavRL：动态环境中的安全飞行学习
[![Python](https://img.shields.io/badge/python-3.10-4B8BBE.svg)](https://docs.python.org/3/whatsnew/3.10.html)
[![ROS1](https://img.shields.io/badge/ROS1-Noetic-green.svg)](https://wiki.ros.org/noetic)
[![ROS2](https://img.shields.io/badge/ROS2-Humble-F39C12.svg)](https://docs.ros.org/en/humble/index.html)
[![IsaacSim](https://img.shields.io/badge/IsaacSim-NVIDIA-C0392B.svg)](https://docs.omniverse.nvidia.com/isaacsim/latest/overview.html)
[![Linux platform](https://img.shields.io/badge/platform-Ubuntu-27AE60.svg)](https://releases.ubuntu.com/22.04/)

这是一个基于开源 `NavRL` 框架整理和扩展的中文项目说明仓库，重点展示我在 `Isaac Sim` 环境下围绕四旋翼无人机强化学习动态避障所做的训练流程改进、评估脚本补充、展示素材整理与文档重构工作。

## 上游工作与论文链接

- 原论文：[`NavRL: Learning Safe Flight in Dynamic Environments`](https://ieeexplore.ieee.org/document/10904341)
- IEEE Xplore：<https://ieeexplore.ieee.org/document/10904341>
- 预印本：<https://arxiv.org/pdf/2409.15634>
- YouTube 演示：<https://youtu.be/EbeJW8-YlvI>
- Bilibili 演示：<https://www.bilibili.com/video/BV1gsA9eTErz/?share_source=copy_web&vd_source=1333db331406abb1b5d4cece1e253427>
- 上游项目仓库：<https://github.com/Zhefan-Xu/NavRL>

<table>
  <tr>
    <td><img src="media/NavRL-demo1.gif" style="width: 100%;"></td>
    <td><img src="media/NavRL-demo2.gif" style="width: 100%;"></td>
    <td><img src="media/NavRL-demo3.gif" style="width: 100%;"></td>
  </tr>
</table>

## 仓库内容概览

这个仓库主要包含两部分内容：

- **上游 NavRL 原始能力**
  - 包括论文对应的训练、部署和 ROS 相关工程结构
- **我基于 `isaac-training` 子项目做的改进与整理**
  - 环境逻辑与奖励函数修改
  - 批量回放与批量评估脚本
  - 中文说明文档与展示材料整理
  - 简历版 / 毕设版项目表达文档

更准确地说，这个项目不是从零发明一套新的强化学习算法，而是**基于 NavRL / OmniDrones 的现有训练框架，对 Isaac Sim 训练链路做工程化改进与结果整理**。

## 我主要完成的工作

- **环境与任务定义优化**
  - 修改重置逻辑，减少沿地图边缘绕飞的问题
  - 约束动态障碍生成位置，保护起点 / 终点关键通道
- **奖励与训练稳定性改进**
  - 加入姿态稳定性相关惩罚，缓解首次避障后的后段失稳
  - 配合课程学习思路逐步增加动态障碍难度
- **评估与展示工具链建设**
  - 批量导出 `mp4/png`
  - 批量输出 `csv/json/md`
  - 明确区分 `showcase pass` 与 `evaluation success`
- **项目文档整理**
  - 将训练、复现、结果和贡献边界整理为中文说明文档

## 建议优先阅读的文档

如果你主要关心我这次实际修改的部分，建议先看：

- [`isaac-training/README.md`](isaac-training/README.md)
- [`isaac-training/REPRODUCIBILITY_CN.md`](isaac-training/REPRODUCIBILITY_CN.md)
- [`isaac-training/INTERNSHIP_PROJECT_CN.md`](isaac-training/INTERNSHIP_PROJECT_CN.md)
- [`isaac-training/GRADUATION_DESIGN_CN.md`](isaac-training/GRADUATION_DESIGN_CN.md)

## 当前结果如何阅读

当前仓库中与结果相关的材料分为两类：

- **`media/*.png` 与 `media/*.mp4`**
  - 更适合做展示材料
  - 通常对应单个 `seed` 的一次 20 环境批量回放
- **`media/results/*.md`**
  - 更适合做正式结果说明
  - 默认是多 `seed` 汇总后的统计结果

因此：

- `png/mp4` 与 `summary.md` 的统计口径相关
- 但它们的数值**不一定完全相等**
- 如果需要正式表述，应优先引用 `media/results/*.md`

## 当前可直接引用的结果文件

- [`isaac-training/media/results/static_120_summary.md`](isaac-training/media/results/static_120_summary.md)
- [`isaac-training/media/results/dynamic_120_16_summary.md`](isaac-training/media/results/dynamic_120_16_summary.md)
- [`isaac-training/media/results/dynamic_100_32_summary.md`](isaac-training/media/results/dynamic_100_32_summary.md)
- [`isaac-training/media/results/dynamic_120_32_summary.md`](isaac-training/media/results/dynamic_120_32_summary.md)

## 快速入口

### 训练

```bash
bash isaac-training/train.sh
```

### 回放

```bash
bash isaac-training/back.sh
```

### 批量导出演示素材

```bash
bash isaac-training/capture_demo_videos.sh static_120_success
bash isaac-training/capture_demo_videos.sh dynamic_120_16_failure_analysis
bash isaac-training/capture_demo_videos.sh dynamic_100_32_stress
bash isaac-training/capture_demo_videos.sh dynamic_120_32_success
```

### 批量统计结果

```bash
bash isaac-training/evaluate_demo_cases.sh static_120
bash isaac-training/evaluate_demo_cases.sh dynamic_120_16
bash isaac-training/evaluate_demo_cases.sh dynamic_100_32
bash isaac-training/evaluate_demo_cases.sh dynamic_120_32
```

## 上游项目入口

如果你希望继续查看原始开源项目能力，可重点关注：

- `quick-demos/`
- `ros1/`
- `ros2/`
- `isaac-training/setup.sh`
- `isaac-training/setup_deployment.sh`

更详细的原始训练 / 部署说明，建议结合上游仓库与论文一起阅读。

## 引用信息

如果原始 NavRL 工作对你的研究有帮助，请优先引用原论文：

```bibtex
@ARTICLE{NavRL,
  author={Xu, Zhefan and Han, Xinming and Shen, Haoyu and Jin, Hanyu and Shimada, Kenji},
  journal={IEEE Robotics and Automation Letters},
  title={NavRL: Learning Safe Flight in Dynamic Environments},
  year={2025},
  volume={10},
  number={4},
  pages={3668-3675},
  keywords={Navigation;Robots;Collision avoidance;Training;Safety;Vehicle dynamics;Heuristic algorithms;Detectors;Autonomous aerial vehicles;Learning systems;Aerial systems: Perception and autonomy;reinforcement learning;collision avoidance},
  doi={10.1109/LRA.2025.3546069}
}
```

## 致谢

- 原始 NavRL 工作作者：Zhefan Xu, Xinming Han, Haoyu Shen, Hanyu Jin, Kenji Shimada
- 上游 Isaac Sim 训练部分构建于 [`OmniDrones`](https://github.com/btx0424/OmniDrones)
- 本仓库中的中文整理、实验展示材料与 Isaac-training 相关改动，为我基于开源项目所做的二次工程化整理
