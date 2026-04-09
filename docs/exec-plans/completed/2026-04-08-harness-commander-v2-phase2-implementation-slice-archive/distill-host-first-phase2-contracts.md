# Harness-Commander V2 `distill` Phase 2 宿主模型默认路径与实现切片

## Goal

把 `distill` 从 Phase 1 的 deterministic baseline 推进到可实施、可验证的 Phase 2 implementation slice，固定默认入口、fallback 语义、兼容模式边界与测试矩阵。

## Context

- V2 Phase 1 已完成并归档：
  - `distill` 已具备 `heuristic` / `host-model` / `auto`
  - `extraction_report`、`section_sources`、`source_mapping_coverage` 已形成基础结果协议
  - failure / fallback / artifact / summary / meta 一致性已补齐
- V2 Phase 2 已确认：
  - `distill` 是第一批必须进入宿主模型默认主路径的命令之一
  - Harness 继续控制最终状态、产物路径、fallback 事实和结构化结果合同
- 当前实现缺口：
  - 默认入口仍需明确为 `auto`
  - `auto` 的 provider 缺失与 host 失败需要稳定回退到 heuristic
  - 需要新增 execution-path 级留痕，而不只是保留兼容字段

## Slice Decision

- 不新增 CLI 模式，继续使用：`heuristic` / `host-model` / `auto`
- 默认入口切为 `auto`
- `auto` 是当前唯一的 host-first 入口：
  - provider 可用时优先宿主模型
  - provider 缺失时回退 heuristic
  - host 运行失败、空结果、结构不完整时回退 heuristic
- 显式 `heuristic` 继续表示 deterministic baseline
- 显式 `host-model` 继续表示强制宿主模型入口：
  - provider 缺失仍为 `failure`
- 本切片不新增 coverage threshold，不扩新的 runtime，不改产物路径

## Minimal Closed Loop

### 输入

- `harness distill <source>`
- 现有 `--mode heuristic|host-model|auto`
- 可选 `--provider <name>`
- provider config

### 输出

- 兼容字段：
  - `distill_mode`
  - `extraction_source`
  - `fallback_from`
  - `fallback_reason`
- Phase 2 新留痕：
  - `execution_path`
  - `host_attempted`
  - `host_first`
- 结构化字段：
  - `extraction_report`
  - `section_sources`
  - `source_mapping_coverage`

### 阻断条件

- 源文档不存在：`failure`
- `--mode host-model` 且 provider 缺失：`failure`
- fallback 后仍 `distillation_insufficient`：`failure`

### fallback

- 仅 `auto` 允许回退到 heuristic
- 回退触发条件：
  - provider 缺失
  - host 调用失败
  - host 返回空结构或结构不完整
- fallback 后命令至少 `warning`
- fallback 不得伪装成 host-model 成功

## ULW 1：固定默认入口与兼容模式边界

### 目标

- 把默认模式从“旧 heuristic 心智”切到 `auto`，但不删除兼容模式。

### 验收标准

- 不传 `--mode` 时，`meta.distill_mode = auto`
- `--mode heuristic` 不尝试宿主模型
- `--mode host-model` 缺 provider 时稳定 `failure`

## ULW 2：固定 auto fallback 语义

### 目标

- 让 `auto` 变成真正的 host-first with deterministic fallback。

### 验收标准

- provider 缺失时：
  - `fallback_from = host-model`
  - `fallback_reason = provider_not_configured`
  - `execution_path = heuristic_fallback`
- host 失败或结构不完整时：
  - 继续回退 heuristic
  - warning / summary / meta 指向同一份退化事实

## ULW 3：补齐 Phase 2 留痕合同

### 目标

- 让调用方能区分“请求了什么”和“实际走了什么”。

### 验收标准

- `meta.execution_path`、`meta.host_attempted`、`meta.host_first` 存在
- `meta.extraction_report` 同步保留上述事实
- `summary`、`warnings`、`meta` 不出现事实漂移

## ULW 4：形成测试与验收入口

### 目标

- 让当前实现切片可直接通过 CLI / integration 回归验证。

### 涉及范围

- `docs/product-specs/v2/commands/distill/testing.md`
- `docs/product-specs/v2/commands/distill/acceptance.md`
- `tests/test_cli.py`
- `tests/test_integration.py`

### 验收标准

- 默认 `auto` 成功路径有 CLI / integration 覆盖
- 默认 `auto` fallback 路径有 CLI / integration 覆盖
- `distillation_insufficient` 与 dry-run 继续有回归覆盖

## Non-Goals

- 不新增新的 `distill` CLI 参数或模式
- 不实现增量 distill
- 不实现跨文件聚合提炼
- 不引入 chunk 级来源引用系统
- 不把 coverage 变成新的命令级 gate
- 不新增 provider policy 层

## 当前落实状态

- 已锁定：
  - 默认入口为现有 `auto`
  - `auto` 缺 provider 时回退 heuristic，而不是直接命令失败
  - `host-model` 继续保持显式 provider prerequisite
  - unmatched / coverage 继续沿用 Phase 1 语义
- 已回写：
  - `docs/product-specs/v2/commands/distill/product.md`
  - `docs/product-specs/v2/commands/distill/protocol.md`
  - `docs/product-specs/v2/commands/distill/testing.md`
  - `docs/product-specs/v2/commands/distill/acceptance.md`
- 下一步：
  - 跑 CLI / integration 回归
  - 完成 acceptance 判断与归档决策

## References

- `AGENTS.md`
- `docs/design-docs/harness-engineering.md`
- `docs/exec-plans/active/harness-commander-v2/index.md`
- `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- `docs/product-specs/v2/index.md`
- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/distill/protocol.md`
