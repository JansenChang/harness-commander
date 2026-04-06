# `harness init` 协议

| 项目 | 定义 |
| --- | --- |
| 命令 | `harness init` |
| 参数 | `-p, --root`；`--dry-run` |
| 默认行为 | 未传 `-p` 时使用当前工作目录 |
| 写入行为 | 创建缺失目录和文件；已存在项标记为 `skipped` |
| JSON `meta` | `root`、`dry_run`、`created_count`、`skipped_count`、`template_source` |
| 宿主模型 | 否 |
