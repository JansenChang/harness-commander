# `harness plan-check` 协议

| 项目 | 定义 |
| --- | --- |
| 命令 | `harness plan-check <plan_path>` |
| 参数 | `-p, --root`；`<plan_path>` |
| 必填参数 | `plan_path` |
| 写入行为 | 无 |
| JSON `meta` | `root`、`plan_path` |
| 宿主模型 | 当前默认不接宿主模型；未来仅可辅助生成摘要或修复建议 |
| Harness 职责 | 决定通过/失败语义和问题清单结构 |
