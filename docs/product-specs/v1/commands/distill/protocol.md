# `harness distill` 协议

| 项目 | 定义 |
| --- | --- |
| 命令 | `harness distill <source>` |
| 参数 | `-p, --root`；`<source>`；`--mode heuristic\|host-model\|auto`；`--provider <name>`（临时 override，可选）；`--dry-run` |
| 默认模式 | `heuristic` |
| 产物落点 | `docs/references/` |
| JSON `meta` | `root`、`source_path`、`target_path`、`dry_run`、`source_name`、`target_name`、`source_type`、`extracted_section_count`、`unresolved_sections`、`distill_mode`、`extraction_source`、`fallback_from`、`fallback_reason`、`model_provider`、`model_name`、`provider`、`provider_source` |
| 宿主模型 | 仅在 `host-model` / `auto` 模式下辅助提炼四类核心信息 |
| Harness 职责 | 固定输出模板、文件名规则、路径、warning/error 语义与 fallback 规则 |

## 模式语义

- `heuristic`：完全使用 Harness 本地规则提炼，不调用宿主模型。
- `host-model`：默认读取项目已配置 provider，也允许显式 `--provider` 临时覆盖。
- `auto`：默认读取项目已配置 provider，优先尝试宿主模型；失败时回退到启发式路径。
