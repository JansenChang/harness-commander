# `harness check` 协议

| 项目 | 定义 |
| --- | --- |
| 命令 | `harness check` |
| 参数 | `-p, --root`；`--dry-run` |
| 写入行为 | 无 |
| JSON `meta` | `root`、`dry_run`、`blocking_count`、`warning_count`、`error_count`、`issue_count`、`unquantified_count`、`blocking_reasons`、`checks` |
| 宿主模型 | 当前默认不接宿主模型；未来仅可辅助结果摘要和处理建议措辞 |
| Harness 职责 | 决定规则来源、严重级别、未量化标记和最终状态 |
