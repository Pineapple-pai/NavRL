# NavRL Isaac Training 项目说明（中文版）

## 项目概述

本子项目基于 `NavRL`、`Isaac Sim 4.x` 和 `PPO`，实现了一个面向四旋翼无人机的强化学习导航训练流程，任务目标是在混合静态障碍与动态障碍环境中完成自主穿越。

这项工作的重点并不是重新设计整套 NavRL 算法，而是让 Isaac-training 这部分在本地环境中真正具备：

- 可持续训练
- 可重复调试
- 可视化回放
- 可量化评估
- 可用于简历和项目展示

整个项目主要围绕以下四个实际问题展开：

- 减少无人机沿地图边缘对角线逃逸、绕开障碍场的行为
- 在引入动态障碍后尽量保留原有静态避障能力
- 改善首次避障后姿态摇晃、后续连续碰撞的问题
- 提高训练与回放流程的稳定性，支持反复实验和行为分析

## 项目意义

与纯静态避障相比，动态障碍环境更接近真实应用场景。在真实环境中，无人机不仅要避开墙体、立柱、货架等静态障碍，还需要应对移动人员、车辆、机器人或其他临时干扰目标。相比依赖频繁重规划的传统方法，强化学习在局部动态场景中有机会提供更快的反应速度和更强的适应性。

这个项目展示了一个较完整的研究与工程闭环：

- 基于仿真的策略训练
- 环境设计与奖励函数塑形
- 通过回放定位失败模式
- 从静态到动态的分阶段课程训练
- 将研究代码整理成可展示、可复现的项目说明页

## 技术栈

- `Python 3.10`
- `Isaac Sim 4.x`
- `PyTorch`
- `TorchRL`
- `Hydra`
- `Weights & Biases`（本地多数实验中关闭）
- `NavRL` 上游代码框架
- `OmniDrones` 控制器组件

## 任务设置

无人机需要从地图一侧飞到另一侧，在飞行过程中避开：

- 环境中的静态障碍物
- 在局部范围内移动的动态障碍物

### 观测输入

策略网络使用以下输入：

- 无人机本体状态
- LiDAR 激光雷达观测
- 目标方向
- 动态障碍物特征

### 动作输出

策略输出的是**速度目标**，然后通过：

- `VelController`
- `LeePositionController`

转换为底层可执行的控制命令。

## 我做了哪些修改

以下修改是在上游训练流程基础上完成的。

### 1. 修改重置分布，强制无人机真正穿越障碍场

相关文件：

- `training/scripts/env.py`

核心思路：

- 将无人机起点和目标点放在地图两侧
- 收窄横向自由度，避免它沿边缘绕开障碍区
- 初始化偏航角，使其朝向目标方向

效果：

- 显著减少“对角线逃逸”行为
- 让策略真正学习穿越障碍场，而不是利用地图边缘漏洞

### 2. 增强奖励函数，改善首次避障后的姿态稳定性

相关文件：

- `training/scripts/env.py`

核心思路：

- 保留前进奖励与安全奖励
- 新增角速度惩罚与油门变化惩罚
- 抑制首次避障后姿态摇晃和控制抖动

效果：

- 减少首次避障后的机体不稳定现象
- 改善混合场景中的连续碰撞问题

### 3. 为动态障碍生成加入起点/终点走廊保护

相关文件：

- `training/scripts/env.py`

核心思路：

- 禁止动态障碍生成在起点和终点关键通道附近
- 避免训练初期刚起飞就被堵死、或临近终点被随机障碍封路

效果：

- 引入动态障碍时训练更平滑
- 减少由于不合理场景生成导致的训练退化

### 4. 增加动态障碍数量合法性检查

相关文件：

- `training/scripts/env.py`

核心思路：

- 对不支持的过小 `env_dyn.num_obstacles` 配置进行显式检查
- 避免动态障碍生成逻辑中的除零/非法分配问题

效果：

- 提升实验配置的鲁棒性
- 让错误配置以更清晰的方式暴露出来

### 5. 改善训练与回放工作流

相关文件：

- `training/scripts/train.py`
- `back.sh`

核心思路：

- 优化 checkpoint 恢复逻辑
- 让恢复训练后的步数统计更容易理解
- 在回放侧补充 Vulkan / GPU 环境变量，提升 Isaac Sim 渲染稳定性

效果：

- 更适合反复迭代训练
- 更方便通过回放分析策略行为

## 可量化结果表

下表汇总了实验过程中**明确观察到的关键结果**。

> 说明：这里只列出历史实验中有明确结论的配置。部分中间阶段主要以定性观察为主，并未严格记录成统一百分比。

| 阶段 | 配置 | 主要现象 | 结果 |
| --- | --- | --- | --- |
| 纯静态基线 | `env.num_obstacles=120`，`env_dyn.num_obstacles=0` | 能较稳定穿越高密度静态障碍场 | `约 80% ~ 90%` 通过率 |
| 中等动态密度 | `env.num_obstacles=120`，`env_dyn.num_obstacles=16`，`vel_range=[0.2, 0.4]`，`local_range=[3.0, 3.0, 3.0]` | 动态扰动开始明显影响首次避障后的稳定性 | `约 50% ~ 60%` 通过率 |
| 动态压力测试 | `env.num_obstacles=100`，`env_dyn.num_obstacles=32` | 动态障碍暴露出泛化能力不足 | `约 50%` 通过率 |
| 高密度混合场景 | `env.num_obstacles=120`，`env_dyn.num_obstacles=32`，`vel_range=[0.2, 0.4]`，`local_range=[3.0, 3.0, 3.0]` | 在课程学习和稳定性奖励修正后，混合导航明显更稳定 | `约 70%` 通过率 |

### 奖励函数与运行逻辑修改前后效果

> 说明：下表基于历史实验观察结果整理，属于**工程迭代前后对比**，并非严格单变量学术消融。

| 修改项 | 修改前 | 修改后 | 对应效果 |
| --- | --- | --- | --- |
| 起终点重置逻辑约束 | 无人机会沿边缘或对角线绕飞，训练目标偏离“穿越障碍场” | 起点/终点横向范围收窄，强制穿越障碍区 | 纯静态 `120` 障碍场景下可达到 `约 80% ~ 90%` 通过率，绕飞现象显著减少 |
| 动态障碍走廊保护 | 动态障碍可能在起点/终点附近堵死通路，训练初期退化明显 | 起终点关键走廊禁止生成动态障碍 | 引入动态障碍后训练更平滑，避免“刚起飞就失败”的场景主导训练 |
| 姿态稳定性惩罚（角速度 + 油门变化） | 首次避障后姿态摇晃明显，很多失败最终表现为撞静态障碍 | 奖励中加入角速度与油门变化惩罚，抑制抖动 | `120 + 16` 场景约 `50% ~ 60%`，而在修正后验证的 `120 + 32` 场景可达到 `约 70%`，连续碰撞问题缓解 |
| 动态压力下混合导航 | 动态障碍一旦增多，策略泛化明显退化 | 通过课程学习逐步引入动态障碍，并配合稳定性奖励 | `100 + 32` 场景约 `50%`，`120 + 32` 已验证场景提升到 `约 70%` |
| checkpoint 恢复逻辑 | 恢复训练后步数不直观，难以判断本次新增训练量 | 自动加载最新 checkpoint，并显示实际续训步数 | 训练进度和累计步数更容易解释，便于多轮迭代对比 |
| GUI 回放与运行工作流 | 多环境 GUI 回放负载高，窗口容易卡死，不利于案例展示 | GUI 回放默认单环境，批量成功率评估改为 headless 多环境 | 形成“单案例视频展示 + 多环境概率统计”两条工作流，展示与评估职责分离 |

### 对应回放文件

为了方便查看和展示，建议将上述关键案例与以下视频文件一一对应：

| 实验案例 | 推荐回放文件 | 说明 |
| --- | --- | --- |
| 纯静态基线 | [`media/static_120_baseline.mp4`](media/static_120_baseline.mp4) | 展示 `120` 个静态障碍下的批量回放基线表现 |
| 中等动态密度 | [`media/dynamic_120_16_medium_density.mp4`](media/dynamic_120_16_medium_density.mp4) | 展示 `120 + 16` 配置下的批量回放表现 |
| 动态压力测试 | [`media/dynamic_100_32_stress_test.mp4`](media/dynamic_100_32_stress_test.mp4) | 展示 `100 + 32` 配置下动态压力增大后的批量回放表现 |
| 高密度混合场景 | [`media/dynamic_120_32_high_density_mixed.mp4`](media/dynamic_120_32_high_density_mixed.mp4) | 展示 `120 + 32` 配置下的批量回放表现 |

如果对应视频还没有生成，可以参考 `media/README_CN.md` 中的说明进行导出。

### 四个关键案例的截图与视频

> 说明：以下素材已通过脚本在本地生成。当前版本为便于快速展示的短版素材，使用 `seed=0`、`max_steps=400` 导出。

#### 1. 纯静态基线

截图：

![纯静态基线截图](media/static_120_baseline.png)

视频：

- [`media/static_120_baseline.mp4`](media/static_120_baseline.mp4)

#### 2. 中等动态密度

截图：

![中等动态密度截图](media/dynamic_120_16_medium_density.png)

视频：

- [`media/dynamic_120_16_medium_density.mp4`](media/dynamic_120_16_medium_density.mp4)

#### 3. 动态压力测试

截图：

![动态压力测试截图](media/dynamic_100_32_stress_test.png)

视频：

- [`media/dynamic_100_32_stress_test.mp4`](media/dynamic_100_32_stress_test.mp4)

#### 4. 高密度混合场景

截图：

![高密度混合场景截图](media/dynamic_120_32_high_density_mixed.png)

视频：

- [`media/dynamic_120_32_high_density_mixed.mp4`](media/dynamic_120_32_high_density_mixed.mp4)

对应脚本：

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/capture_demo_videos.sh static_120_success --max-steps 400 --seed 0
bash /home/p/CascadeProjects/NavRL/isaac-training/capture_demo_videos.sh dynamic_120_16_failure_analysis --max-steps 400 --seed 0
bash /home/p/CascadeProjects/NavRL/isaac-training/capture_demo_videos.sh dynamic_100_32_stress --max-steps 400 --seed 0
bash /home/p/CascadeProjects/NavRL/isaac-training/capture_demo_videos.sh dynamic_120_32_success --max-steps 400 --seed 0
```

### 其他重要实验观察

- 纯静态场景中，`env.num_obstacles=160` 时仅部分无人机能够通过。
- 纯静态场景中，`env.num_obstacles=200` 时大量无人机会卡在末段障碍区。
- `env.num_obstacles=50`、`env_dyn.num_obstacles=64` 时性能明显下降，说明在极高动态密度下策略仍会退化。
- 很多动态场景中的最终碰撞其实发生在静态障碍上，说明动态扰动常常先破坏轨迹稳定性，再间接导致静态碰撞。

## 当前训练配置

当前 `training/cfg/train.yaml` 中的配置为：

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

需要注意的是，这一配置更适合视为**当前训练阶段配置**，不应直接作为已经完全验证的最终 benchmark。根据历史实验过程，最清晰验证过的里程碑配置仍然是：

- `120` 个静态障碍
- `32` 个动态障碍
- `vel_range=[0.2, 0.4]`
- `local_range=[3.0, 3.0, 3.0]`

该配置下通过率约为 `70%`。

## 技术贡献边界

为了在简历或面试中准确描述这个项目，需要清楚划分“我做了什么”和“上游项目已经提供了什么”。

### 我直接负责的部分

我直接完成了以下工作：

- 环境重置逻辑修改，使无人机必须穿越障碍场
- 奖励函数修正，提高避障后的姿态稳定性
- 动态障碍生成约束，保护起点/终点关键通道
- 基于实验现象设计课程学习推进路径
- 训练/调试/回放工作流优化
- 基于回放和失败模式进行多轮实验分析与迭代

### 上游项目已提供的部分

以下主要组件由上游 NavRL / OmniDrones 提供：

- 基础 PPO 训练框架
- 核心策略网络结构
- Isaac Sim 环境脚手架
- 速度控制器与 Lee 位置控制器
- 通用机器人/仿真集成逻辑

### 这个项目不应夸大的内容

这个项目**不应宣称**：

- 发明了新的强化学习算法
- 从零重写了整个 NavRL 架构
- 已经完成真实无人机实物闭环部署
- 在标准基准测试上达到严格意义的 SOTA

一个更准确、也更适合简历的表述是：

> 基于 NavRL 框架构建并改进了一个面向四旋翼无人机的 Isaac Sim 动态障碍导航训练流程，通过环境设计、奖励塑形和课程学习优化了静态/动态混合场景下的导航表现。

## 项目结构

与本展示最相关的关键文件如下：

- `training/scripts/env.py`
  - 场景生成
  - 重置逻辑
  - 观测构建
  - 奖励计算
  - 碰撞检测
- `training/scripts/train.py`
  - PPO 训练入口
  - checkpoint 恢复逻辑
  - 训练摘要输出
- `training/scripts/eval.py`
  - 回放/评估入口
- `training/scripts/export_demo_video.py`
  - 导出单个案例演示视频
- `training/scripts/evaluate_case_stats.py`
  - 多 seed、多环境统计成功率/碰撞率
- `training/cfg/train.yaml`
  - 实验配置文件
- `train.sh`
  - 本地训练启动脚本
- `back.sh`
  - 本地回放启动脚本
- `capture_demo_videos.sh`
  - 批量导出演示视频
- `evaluate_demo_cases.sh`
  - 批量输出统计结果表

## 运行方式

### 训练

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/train.sh
```

### 回放

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/back.sh
```

### 示例评估命令

纯静态回放：

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/back.sh env.num_obstacles=120 env_dyn.num_obstacles=0
```

静态 + 动态混合回放：

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/back.sh env.num_obstacles=120 env_dyn.num_obstacles=32 env_dyn.vel_range='[0.2,0.4]' env_dyn.local_range='[3.0,3.0,3.0]'
```

当前更强动态配置回放：

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/back.sh env.num_obstacles=120 env_dyn.num_obstacles=32 env_dyn.vel_range='[0.3,0.5]' env_dyn.local_range='[4.0,4.0,3.0]'
```

### 批量统计命令

如果你要证明“通过率/失败率”，更推荐使用批量 headless 评估：

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh static_120
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh dynamic_120_16
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh dynamic_120_32
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh current_config_120_32
```

结果会输出到：

- `media/results/*.csv`
- `media/results/*_summary.json`
- `media/results/*_summary.md`

其中 `*_summary.md` 最适合直接放到项目展示或答辩材料中。

## 简历友好版项目描述

适合放在简历中的一句话版本：

> 基于 NavRL 与 Isaac Sim 4.x 构建四旋翼无人机强化学习动态避障训练流程，通过修改环境重置逻辑、奖励函数和动态障碍生成约束，提升静态/动态混合场景导航能力，并在 `120` 个静态障碍和 `32` 个动态障碍场景下实现约 `70%` 的通过率。

相关整理文档：

- [`INTERNSHIP_PROJECT_CN.md`](INTERNSHIP_PROJECT_CN.md)
- [`GRADUATION_DESIGN_CN.md`](GRADUATION_DESIGN_CN.md)
- [`REPRODUCIBILITY_CN.md`](REPRODUCIBILITY_CN.md)
- [`PROJECT_BOUNDARY_CN.md`](PROJECT_BOUNDARY_CN.md)

## 可视化材料准备建议

如果你想把这个项目用于简历、面试或作品集，建议同时准备：

- 4 个主展示场景的 `mp4/png`
- `media/results/` 下的批量统计结果

其中需要注意：

- `showcase pass` 主要服务于 PNG 与视频展示
- `evaluation success` 主要服务于正式评估、论文和答辩表述

### 概率/成功率证明材料

如果你想展示“该配置下成功率是多少”，建议不要引用单个视频，而是引用批量统计文件：

- [`media/results/static_120_summary.md`](media/results/static_120_summary.md)
- [`media/results/dynamic_120_16_summary.md`](media/results/dynamic_120_16_summary.md)
- [`media/results/dynamic_100_32_summary.md`](media/results/dynamic_100_32_summary.md)
- [`media/results/dynamic_120_32_summary.md`](media/results/dynamic_120_32_summary.md)

推荐生成命令：

```bash
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh static_120
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh dynamic_120_16
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh dynamic_100_32
bash /home/p/CascadeProjects/NavRL/isaac-training/evaluate_demo_cases.sh dynamic_120_32
```

如果你只想评估某个案例，也可以单独运行对应场景。

### B. README / 作品集 / PPT 建议图表

推荐准备以下图片：

- `figures/result_table.png`
  - 一页结果汇总表
- `figures/curriculum_schedule.png`
  - 从纯静态到 `8 -> 16 -> 32` 个动态障碍的课程推进图
- `figures/failure_modes.png`
  - 典型失败模式：边缘绕飞、动态扰动后撞静态、首次避障后姿态摇晃
- `figures/system_pipeline.png`
  - 观测输入 -> PPO -> 控制器 -> 仿真器 的系统流程图

### C. 回放时建议录制的内容

建议至少录制：

- 一个完整成功案例
- 一个代表性失败案例
- 一个增加稳定性奖励前后的对比视频
- 一个证明“无人机不再沿地图边缘绕飞”的视频

### D. 最小作品集材料包

如果时间有限，至少准备：

- 1 张 README 截图
- 1 张结果表图片
- 1 个混合场景成功视频
- 1 个失败分析视频

这些材料已经足够支撑简历附件、面试展示或个人作品集页面。

## 面试时可强调的点

如果你在面试中介绍这个项目，建议重点突出以下几点：

- 难点不只是“训练一个策略”，而是让训练流程足够稳定，能够支撑反复实验
- 很多动态场景中的失败，本质上是姿态稳定性问题，最终表现为撞静态障碍
- 项目效果的提升主要来自环境设计、奖励塑形和课程学习，而不是盲目更换更大的网络

## 后续可继续优化的方向

如果后续继续完善这个项目，可以考虑：

- 补充角速度惩罚和油门惩罚的消融实验
- 将回放视频和结果图导出到 `media/` 目录
- 继续测试更强动态配置，如更大的 `local_range` 或更高 `vel_range`
- 加入面向 sim-to-real 的噪声和随机化设置
- 整理一页 benchmark 结果页，便于面试时快速展示
