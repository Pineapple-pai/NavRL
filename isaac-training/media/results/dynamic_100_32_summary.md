# dynamic_100_32 评估结果

- checkpoint: `/home/p/NavRL_checkpoints/checkpoint_116000.pt`
- num_seeds: `2`
- overrides: `env.num_obstacles=100 env_dyn.num_obstacles=32`

- showcase pass 定义：`第一回合内曾接近目标，或未碰撞并以 truncated 结束`
- evaluation success 定义：`第一回合内连续 5 步进入目标区，且回合最终不是 terminated`

- 统计范围说明：`本文件是多 seed 汇总结果；PNG/MP4 通常只对应单个 seed 的一次 20 环境展示回放，因此数值不一定与本表完全相等。`

| 指标 | 数值 |
| --- | --- |
| 平均回报 | `12624.6538` |
| 平均回合长度 | `1562.2250` |
| 原始 reach_goal 率 | `0.0000` |
| 目标区接触率 | `0.3500` |
| 展示通过率（showcase pass） | `0.6500` |
| 正式成功率（evaluation success） | `0.3250` |
| 碰撞率 | `0.3500` |
| 截断率 | `0.6500` |
