# `harness collect-evidence` 协议

| 项目 | 定义 |
| --- | --- |
| 命令 | `harness collect-evidence` |
| 参数 | `-p, --root`；`--command <text>`；`--exit-code <int>`；`--summary <text>`；`--status <text>`；`--log <text>`；`--dry-run` |
| 产物落点 | `docs/generated/evidence/` |
| JSON `meta` | `root`、`evidence_path`、`dry_run` |
| 宿主模型 | 默认不接宿主模型；未来最多可辅助生成更易读摘要，但不能改写原始事实 |
| Harness 职责 | 固定证据字段、命名规则、落盘位置和结果状态 |
