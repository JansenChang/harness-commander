# `harness propose-plan` 协议

| 项目 | 定义 |
| --- | --- |
| 命令 | `harness propose-plan` |
| 参数 | `-p, --root`；`--input <text>`；`--dry-run` |
| 必填参数 | `--input` |
| 产物落点 | `docs/exec-plans/active/` |
| JSON `meta` | `root`、`request`、`dry_run`、`plan_path`、`ulw_count`、`references` |
| 宿主模型 | 当前未实现；未来可辅助需求整理、计划内容生成、ULW 拆分 |
| Harness 职责 | 固定模板、引用要求、落盘路径、结果协议 |
