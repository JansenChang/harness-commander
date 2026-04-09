# V2 `distill` 验收定义

## 当前状态

- active（Phase 2 implementation slice）

## 验收范围

- 验收当前实现切片：
  - 默认入口切到 `auto`
  - `auto` 在 provider 可用时优先宿主模型
  - `auto` 在 provider 缺失或宿主模型失败时回退 heuristic
  - `heuristic` / `host-model` 显式兼容入口保持可用
  - `execution_path` / `host_attempted` / `host_first` 留痕稳定
  - 来源映射、artifact、summary、fallback 事实一致
- 不验收：
  - 增量 distill
  - 跨文件聚合提炼
  - chunk 级引用系统
  - coverage threshold 新 gate

## 验收标准

### AC1 默认入口切换完成

- 不传 `--mode` 时：
  - `meta.distill_mode = auto`
  - 命令不再默认走 `heuristic`

### AC2 host-first 成功路径稳定

- provider 可用时：
  - `meta.extraction_source = host-model`
  - `meta.execution_path = host-model`
  - `meta.host_attempted = true`
  - `fallback_from = null`

### AC3 auto fallback 语义稳定

- provider 缺失时：
  - 不直接命令失败
  - `meta.extraction_source = heuristic`
  - `meta.fallback_from = host-model`
  - `meta.fallback_reason = provider_not_configured`
  - `meta.execution_path = heuristic_fallback`
  - 命令至少为 `warning`
- 宿主模型失败或结构不完整时：
  - 继续回退 heuristic
  - warning / summary / meta 保持同一份 fallback 事实

### AC4 显式兼容入口不回归

- `--mode heuristic`：
  - 继续走 deterministic baseline
  - 来源映射与 coverage 语义不回归
- `--mode host-model`：
  - provider 可用时成功
  - provider 缺失时稳定 `failure`

### AC5 失败与产物语义一致

- `distillation_insufficient`：
  - 命令 `failure`
  - `meta.extraction_report`、`meta.section_sources`、`meta.source_mapping_coverage` 仍返回
  - 不生成正式 `*-llms.txt`
- dry-run：
  - `artifacts` 为 `would_create` / `would_overwrite`
  - `summary` 不伪造正式落盘

## 验收步骤

1. 跑默认 `auto` + provider 可用路径，确认进入宿主模型。
2. 跑默认 `auto` + provider 缺失路径，确认 fallback 到 heuristic。
3. 跑 `auto` + host-model 失败路径，确认 fallback 留痕稳定。
4. 跑显式 `heuristic` 路径，确认 deterministic baseline 不回归。
5. 跑显式 `host-model` 无 provider 路径，确认稳定 `failure`。
6. 跑 `distillation_insufficient` 与 dry-run，确认 artifact / summary / meta 一致。

## 判定规则

- 任一 AC 不满足，则当前 `distill` Phase 2 implementation slice 验收不通过。
- 所有 AC 满足后，才可进入：
  - coverage threshold 讨论
  - 更细粒度来源引用
  - 增量 distill
