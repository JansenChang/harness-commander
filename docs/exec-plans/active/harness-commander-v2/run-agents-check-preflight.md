# Harness-Commander V2 `run-agents` 治理前置门执行计划

## Goal

把 `check` 正式接入 `run-agents` 的前置门，让 V2 最小闭环从“命令分别存在”升级为“工作流真正串起来”，并保持 deterministic baseline 与现有结果协议可解释。

## Context

- `run-agents` 已完成 Phase 1 阶段合同基线。
- `check` 已完成治理入口结果协议，能返回：
  - `health_score`
  - `governance_entry`
  - `next_actions`
- 当前两者仍然是分离命令，`run-agents` 未实际消费 `check` 结果。
- 下一步最合理的不是扩并发 runtime，而是先把治理前置门串进主链。

## Business Logic

- `run-agents` 应在 requirements 之前执行一次治理预检。
- 本轮前置门先采用保守策略：
  - `check` 返回 `failure` 时，阻断 `run-agents`
  - `check` 返回 `warning` 时，允许继续，但必须显式留痕
  - `check` 返回 `success` 时，正常继续
- 前置门必须进入：
  - `meta.agent_runs`
  - `meta.stage_contracts`
- 结果语义必须让人和后续 agent 都能看出：
  - 是否执行了治理预检
  - 是否被阻断
  - 如果没阻断，仍有哪些 warning 被带入主流程

## Scope

- 在 `run-agents` 中新增 `check` 预检阶段
- 更新 `run-agents` 的产品、协议、测试、验收文档
- 补 CLI / integration 覆盖
- 保持 `check` 命令自身结果协议不变

## Non-Goals

- 不把 `check` 变成宿主模型驱动前置门
- 不让 `warning` 一律阻断 `run-agents`
- 不引入并发 agent runtime
- 不把 `distill` 或 `collect-evidence` 自动并入主链

## ULW 1: 锁定治理前置门语义

### 目标

- 明确 `run-agents` 如何消费 `check` 结果，以及何时阻断、何时仅留痕。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`
- `src/harness_commander/application/commands.py`

### 验收标准

- `check` 作为正式前置阶段进入 `run-agents`。
- `check.failure` 阻断后续阶段。
- `check.warning` 不阻断 requirements，但会进入 warning / stage contract。

## ULW 2: 把前置门接入结果协议

### 目标

- 让 `run-agents` 结果中稳定反映治理预检事实。

### 涉及范围

- `src/harness_commander/application/commands.py`
- `tests/test_cli.py`
- `tests/test_integration.py`

### 验收标准

- `agent_runs` 增加 `check` 阶段。
- `stage_contracts` 增加 `check` 阶段，并包含治理入口摘要。
- 阻断场景下能明确看见 `check` 阶段失败和后续未开始。

## ULW 3: 保持兼容并补齐覆盖

### 目标

- 在引入治理前置门的同时，保持现有 `run-agents` 协议可用。

### 涉及范围

- `tests/test_cli.py`
- `tests/test_integration.py`
- `docs/product-specs/v2/commands/run-agents/testing.md`
- `docs/product-specs/v2/commands/run-agents/acceptance.md`

### 验收标准

- 覆盖：
  - `check` 阻断时的 failure
  - `check` warning 但继续执行
  - `check` success 正常继续
- 现有 verify / pr-summary 逻辑不回归。

## ULW 4: 为下一轮强前置门和自动消费留扩展位

### 目标

- 让当前前置门策略可以继续演进，而不是临时拼接。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/product-planning.md`
- `docs/exec-plans/tech-debt-tracker.md`
- `docs/design-docs/harness-engineering.md`

### 验收标准

- 当前策略明确记录为：
  - failure 阻断
  - warning 留痕但继续
- 下一轮若要升级为更强门禁，不需要推翻当前字段结构。

## Acceptance Criteria

- `run-agents` 在 requirements 前执行 `check` 预检。
- `check.failure` 阻断 `run-agents`。
- `check.warning` 继续执行但结果留痕。
- 文档、代码、测试同步更新。

## Exception Handling

- 如果 `check` 结果缺少必要治理字段，优先回退到保守阻断，而不是伪造可继续。
- 如果前置门接入破坏现有 `verify` / `pr-summary` 语义，必须回退并修正。
- 若显式 `--plan` 与默认 active 计划入口语义不一致，应以 `run-agents` 当前输入为准，不依赖默认扫描推断。

## Verification

- 运行 `pytest tests/test_cli.py tests/test_integration.py -k run_agents`
- 检查 `check` failure / warning / success 三类预检场景
- 检查 verify / pr-summary 既有场景不回归

## References

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/PLANS.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/design-docs/harness-engineering.md`
- `docs/product-specs/v2/commands/check/product.md`
- `docs/product-specs/v2/commands/run-agents/product.md`
