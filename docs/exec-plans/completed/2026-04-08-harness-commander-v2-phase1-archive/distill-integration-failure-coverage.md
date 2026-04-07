# Harness-Commander V2 `distill` 集成失败路径补强执行计划

## Goal

补齐 `distill` 在 integration 层的失败与边界路径覆盖，并收敛 failure 路径的产物语义，避免当前只在 CLI 层锁住 `distillation_insufficient`、provider 缺失等语义，导致真实入口链路回归时无人发现。

## Context

- `distill` Phase 1 已完成来源映射与 extraction report 基线。
- 当前 CLI 测试已覆盖：
  - `partial_distillation`
  - `distillation_insufficient`
  - `provider_not_configured`
  - host-model / auto fallback
- 当前 integration 测试主要覆盖：
  - heuristic 成功路径
  - host-model 成功路径
  - auto fallback 路径
- 这意味着真实 CLI 入口链路下的失败路径仍存在“协议已定义、CLI 已测、integration 未锁”的空洞。
- 额外发现：
  - `distillation_insufficient` 时当前实现仍会写出 `docs/references/*-llms.txt`
  - failure 状态与落盘产物事实出现漂移

## Business Logic

- `distill` 的 failure / edge path 不能只靠单层 CLI 测试保护。
- integration 层至少要锁住两类真实风险：
  - 真实输入不足时，`distillation_insufficient` 仍返回稳定 failure 结果与映射结构，且不生成正式产物
  - 真实 host-model 入口缺少 provider 时，`provider_not_configured` 仍以稳定 failure 暴露
- 文档中的测试与验收定义要同步反映这些失败路径，而不是只写成功与 fallback。

## Scope

- 更新 `distill` 的测试/验收文档
- 新增 `distill` integration 失败与边界路径测试
- 修正 `distillation_insufficient` 时仍写正式产物的实现
- 如测试暴露真实协议偏移，则修正实现

## Non-Goals

- 不扩展 `distill` 模式或结果字段
- 不实现增量 distill
- 不引入跨文件聚合
- 不切换宿主模型默认优先主路径

## ULW 1: 锁定失败路径测试目标

### 目标

- 把 `distill` integration 层必须保护的 failure / edge path 写进仓库事实源。

### 涉及范围

- `docs/product-specs/v2/commands/distill/testing.md`
- `docs/product-specs/v2/commands/distill/acceptance.md`

### 验收标准

- 文档明确要求 integration 层覆盖：
  - `distillation_insufficient`
  - `provider_not_configured`
- 文档继续强调 failure 时新旧字段必须共享同一份事实，且不得伪造正式产物。

## ULW 2: 补齐 integration 失败路径覆盖

### 目标

- 让真实入口链路对 `distill` failure / edge path 有防回归测试。

### 涉及范围

- `tests/test_integration.py`

### 验收标准

- 新增 integration 用例覆盖：
  - 输入不足导致 `distillation_insufficient`
  - host-model 无 provider 导致 `provider_not_configured`
- 断言结果包含稳定 `status`、`errors`、`meta` 映射结构。
- 断言 `distillation_insufficient` 时无 artifact、无真实落盘。

## ULW 3: 校验实现与协议一致

### 目标

- 如果测试暴露真实实现与协议不一致，直接在本轮修正。

### 涉及范围

- `src/harness_commander/application/commands.py`
- `tests/test_cli.py`
- `tests/test_integration.py`

### 验收标准

- 全量 `distill` 相关测试通过。
- `distillation_insufficient` 时不再创建正式参考材料文件。

## Acceptance Criteria

- `distill` integration 层存在真实失败路径覆盖。
- `distillation_insufficient` 在 integration 层返回稳定 failure 协议。
- `distillation_insufficient` 时不生成正式参考材料产物。
- `provider_not_configured` 在 integration 层返回稳定 failure 协议。
- 文档、测试、实现保持一致。

## Exception Handling

- 如果新增 integration 用例暴露实现与文档不一致，优先修实现或文档之一，不能保留漂移。
- 如果发现 failure 场景下 artifact、summary、meta 指向不同事实，必须在本轮收敛。

## Verification

- `pytest -q tests/test_cli.py -k distill`
- `pytest -q tests/test_integration.py -k distill`
- 如有必要，`pytest -q`

## References

- `AGENTS.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/distill/protocol.md`
- `docs/product-specs/v2/commands/distill/testing.md`
