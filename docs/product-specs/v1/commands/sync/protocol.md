# `harness sync` 协议

| 项目 | 定义 |
| --- | --- |
| 命令 | `harness sync` |
| 参数 | `-p, --root`；`--dry-run` |
| 产物落点 | `docs/generated/`、`docs/references/` |
| dry-run | 返回 `would_update`，不实际写入 |
| JSON `meta` | `root`、`dry_run`、`change_count`、`change_types`、`changes` |
| 宿主模型 | 当前默认不接宿主模型；未来仅可辅助生成更新说明或参考内容 |
| Harness 职责 | 决定是否触发、影响范围、目标路径、结果协议 |
