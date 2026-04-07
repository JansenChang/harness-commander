# Harness-Commander V2 `check` ready 集成覆盖执行计划

## Goal

补齐 `check` 在 integration 层缺失的 real ready 场景，避免当前只锁住 blocking / warning，而把“真正可进入 `run-agents`”的成功入口留在未验证状态。

## Context

- `check` Phase 1 已完成：
  - `health_score`
  - `governance_entry`
  - `next_actions`
- 当前 CLI 测试已覆盖 blocking / warning / 默认目标元信息。
- 当前 integration 测试已覆盖：
  - 阻断场景（secret exposure）
  - warning 场景（unquantified rule sources）
- 仍缺一条真实 ready 场景，用来证明：
  - `status=success`
  - `governance_entry.status=ready`
  - `ready_for_run_agents=true`
  - `next_actions` 返回 `proceed`

## Business Logic

- `check` 是治理入口，不只负责“发现坏状态”，也必须稳定表达“当前可以继续”。
- 如果 integration 层不锁 ready 场景，后续对模板、规则量化标准、默认检查目标的改动，可能把 success 入口悄悄打回 warning 而无人发现。
- 本轮只补真实 ready 场景，不扩扫描域。

## Scope

- 新增 `check` ready integration 测试
- 更新 active exec plan 索引和产品规划中的当前阶段说明
- 在技术债台账记录这次 AI 漏测补洞

## Non-Goals

- 不修改 `check` 协议字段
- 不新增扫描规则
- 不把 `check` 再次并入其他命令主链

## ULW 1: 锁定 real ready 场景

### 目标

- 证明真实仓库上下文下，`check` 可以稳定给出 ready 入口。

### 涉及范围

- `tests/test_integration.py`

### 验收标准

- 存在一条 ready 集成测试
- 断言 `status=success`
- 断言 `governance_entry.status=ready`
- 断言 `ready_for_run_agents=true`
- 断言 `next_actions[0].code=proceed`

## ULW 2: 收敛当前阶段导航

### 目标

- 避免 active 索引仍停留在已完成的 `distill` 失败路径补洞。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/index.md`
- `docs/exec-plans/active/harness-commander-v2/product-planning.md`

### 验收标准

- active index 当前阶段切到 `check` ready 集成覆盖
- product planning 的当前选择反映这一步

## ULW 3: 留下 AI 漏测留痕

### 目标

- 把“协议文档要求 ready，但 integration 没测”的历史空洞记入仓库。

### 涉及范围

- `docs/exec-plans/tech-debt-tracker.md`

### 验收标准

- 技术债台账新增对应记录
- 记录现象、根因、修复方式、防复发

## Acceptance Criteria

- `check` ready 场景在 integration 层可稳定通过。
- active exec plans 当前阶段导航准确。
- AI 漏测事件已留痕。

## 当前进度

- 已完成：
  - `tests/test_integration.py` 新增 real ready 场景
  - active index 已切到当前阶段并同步进度
  - 技术债台账已记录本次漏测补洞
- 已验证：
  - `pytest -q tests/test_integration.py -k check`
  - `pytest -q tests/test_cli.py -k check`
  - `pytest -q`
- 当前状态：
  - 本计划目标已达成
  - 暂不归档，等待确认下一轮是否继续推进 `check` 或切到其他命令

## Exception Handling

- 若 ready 场景难以构造，优先在测试里显式写出可量化规则和默认目标，而不是降低断言标准。
- 若新增测试暴露 `check` 实现 bug，优先修实现并保留测试。

## Verification

- `pytest -q tests/test_integration.py -k check`
- `pytest -q`

## References

- `AGENTS.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/product-specs/v2/commands/check/testing.md`
- `docs/product-specs/v2/commands/check/acceptance.md`
