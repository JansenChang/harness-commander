# V2 `distill` 协议定义

## 当前状态

- phase1-complete / phase2-implementation-slice

## CLI 入口

| 项 | 定义 |
| --- | --- |
| 命令 | `harness distill <source>` |
| 参数 | `-p, --root`；`<source>`；`--mode heuristic\|host-model\|auto`；`--provider <name>`；`--dry-run` |
| 默认模式 | `auto` |

## 模式语义

- `heuristic`
  - 强制本地规则提炼
  - 不尝试宿主模型
- `host-model`
  - 强制尝试宿主模型入口
  - provider 缺失时命令 `failure`
- `auto`
  - Phase 2 的默认 host-first 入口
  - provider 可用时优先尝试宿主模型
  - provider 缺失、宿主模型失败或返回结构不完整时，回退到 heuristic

## 结果协议总览

- 保持现有兼容字段：
  - `distill_mode`
  - `extraction_source`
  - `fallback_from`
  - `fallback_reason`
  - `extracted_section_count`
  - `unresolved_sections`
  - `provider`
  - `provider_source`
  - `execution_path`
  - `host_attempted`
- 保持现有结构化字段：
  - `extraction_report`
  - `section_sources`
  - `source_mapping_coverage`
  - `host_first`

## Phase 2 host-first 留痕

- `meta.execution_path`
  - `heuristic`
  - `host-model`
  - `heuristic_fallback`
- `meta.host_attempted`
  - 是否真实尝试过宿主模型
- `meta.host_first`
  - `mode`
  - `host_model_allowed`
  - `preferred_path`
  - `provider`
  - `provider_configured`
  - `provider_source`
  - `provider_resolution_reason`
  - `host_attempted`
  - `selected_path`
  - `fallback_applied`
  - `fallback_from`
  - `fallback_reason`
- `meta.extraction_report` 必须同步保留：
  - `execution_path`
  - `host_attempted`
  - `host_first`

## Phase 2 状态语义

- 默认 `auto` 成功走宿主模型：
  - `meta.distill_mode = auto`
  - `meta.extraction_source = host-model`
  - `fallback_from = null`
- 默认 `auto` 发生 fallback：
  - `meta.distill_mode = auto`
  - `meta.extraction_source = heuristic`
  - `fallback_from = host-model`
  - `fallback_reason` 必须存在
  - `execution_path = heuristic_fallback`
  - 命令最终至少为 `warning`
- `host-model` 缺少 provider：
  - 命令 `failure`
  - 错误码 `provider_not_configured`
- `distillation_insufficient`：
  - 继续是命令级 `failure`
  - `meta.extraction_report`、`meta.section_sources`、`meta.source_mapping_coverage` 仍需返回
  - `artifacts` 必须为空

## fallback 规则

- 以下场景允许当前 host-attempting 模式回退到 heuristic：
  - `auto` 下 provider 缺失
  - 宿主模型调用失败
  - 宿主模型返回空结构或结构不完整
- `host-model` 的 provider prerequisite 仍是严格边界：
  - provider 缺失时直接 `failure`
- fallback 后必须保留：
  - `warnings[].code = distill_fallback_to_heuristic`
  - `meta.fallback_from`
  - `meta.fallback_reason`
  - `meta.extraction_report.fallback`
- fallback 不允许伪装成完整 host-model 成功。

## 来源映射与 coverage

- `section_sources` / `source_mapping_coverage` 继续由 Harness 生成和校验。
- `unmatched` 继续是允许状态：
  - 不能伪造行号或 snippet
  - 不单独触发 failure
- 当前切片不引入新的 coverage threshold。

## 产物与 dry-run 约束

- 成功或 warning 且未触发 `distillation_insufficient` 时，可生成 `docs/references/*-llms.txt`
- dry-run 下仅返回 `would_create` / `would_overwrite`
- dry-run `summary` 不得伪造“已正式生成参考材料”
- failure 路径下，不允许真实落盘正式参考材料

## Harness 控制边界

- 以下事实继续由 Harness 控制：
  - 最终状态
  - 目标路径
  - fallback 记录
  - `section_sources`
  - `source_mapping_coverage`
  - `extraction_report`
- 宿主模型不接管结果合同和产物事实。

## 当前命令级计划入口

- 当前实现切片归档：
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase2-implementation-slice-archive.md`
- 命令级计划参考：
  - `docs/exec-plans/active/harness-commander-v2/distill-host-first-phase2-contracts.md`
