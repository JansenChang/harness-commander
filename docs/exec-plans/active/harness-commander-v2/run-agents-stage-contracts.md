# Harness-Commander V2 `run-agents` 阶段合同执行计划

## Goal

把 V2 `run-agents` 的阶段合同从产品文档落实到代码与测试中，形成第一轮可执行的 deterministic baseline，为后续恢复、重试、宿主模型参与边界和最小闭环扩展提供稳定结果协议。

## Context

- V2 已确认 `run-agents` 是治理主入口。
- 当前 `run-agents` 仍主要输出阶段摘要，缺少机器可消费的阶段合同字段。
- V2 已确认每个阶段至少要定义：
  - 输入
  - 输出
  - 阻断条件
  - fallback
  - 产物
  - 是否允许宿主模型参加
- 当前阶段默认不依赖宿主模型，因此这轮实现先锁 deterministic baseline，不引入新的 provider runtime 行为。

## Business Logic

- `run-agents` 不是单纯的摘要生成器，而是后续工作流编排的协议入口。
- 第一轮实现不扩展并发 agent runtime，也不把 `collect-evidence` 并入主流程。
- 当前最重要的不是“多做几个阶段”，而是把已有阶段的结果语义结构化。
- 本轮必须同时满足：
  - 不破坏现有 `agent_runs` 使用方式
  - 新增结构化阶段合同字段，供后续 runtime 和宿主模型边界复用
  - 文档、代码、测试三者同步收敛

## Scope

- 更新 V2 `run-agents` 的产品、协议、测试、验收文档
- 为 `run-agents` 增加结构化阶段合同元数据
- 覆盖成功、失败、fallback / 阻断路径
- 保持现有 CLI 参数和 provider 解析行为兼容

## Non-Goals

- 不在本轮引入并发 agent runtime
- 不把 `check`、`distill`、`collect-evidence` 全量并入 `run-agents` 主链
- 不切换到默认优先宿主模型
- 不改动 `install-provider` 生命周期范围

## ULW 1: 锁定阶段合同结构

### 目标

- 明确 `run-agents` 每个阶段在运行时返回的最小结构，消除“只有 summary 没有合同”的状态。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`
- `src/harness_commander/application/commands.py`

### 验收标准

- 阶段合同至少包含：
  - `stage`
  - `status`
  - `inputs`
  - `outputs`
  - `blocking_conditions`
  - `fallback`
  - `artifacts`
  - `host_model_allowed`
- 当前阶段明确 `requirements` / `plan` / `implement` / `verify` / `pr-summary` 的合同差异。
- `verify` 阶段的阻断条件和 `pr-summary` 阶段的生成前提明确可读。

## ULW 2: 把阶段合同落到 `run-agents` 结果协议

### 目标

- 在不破坏现有消费者的前提下，把结构化阶段合同写进命令结果元数据。

### 涉及范围

- `src/harness_commander/application/commands.py`
- `tests/test_cli.py`
- `tests/test_integration.py`

### 验收标准

- `meta` 中新增稳定可断言的阶段合同字段。
- 原有 `agent_runs` 仍保留，避免直接破坏现有调用方。
- verify 缺失 / 非 PASS / verification summary 缺失时，阶段合同仍能反映真实阻断与 fallback 事实。

## ULW 3: 补齐成功 / 失败 / fallback 覆盖

### 目标

- 让 V2 第一轮阶段合同不是只覆盖 happy path。

### 涉及范围

- `tests/test_cli.py`
- `tests/test_integration.py`
- `docs/product-specs/v2/commands/run-agents/testing.md`
- `docs/product-specs/v2/commands/run-agents/acceptance.md`

### 验收标准

- 至少覆盖：
  - verify 通过时的阶段合同
  - verify 缺失时的阻断合同
  - verify 非 PASS 时的阻断合同
  - verification summary 缺失时的 fallback 合同
- 文档中明确 CLI / integration 的验证重点。

## ULW 4: 收敛下一轮扩展输入

### 目标

- 为后续接入 `check` / `distill` / 宿主模型 `requirements` / `plan` 提供稳定扩展位，而不是继续临时堆字段。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/product-planning.md`
- `docs/exec-plans/tech-debt-tracker.md`
- `docs/design-docs/harness-engineering.md`

### 验收标准

- 当前 active plan 能明确说明“这轮只落阶段合同，不扩更大运行时”。
- 若实现中暴露新的临时限制，会记录到技术债台账。
- 下一轮可以直接以阶段合同为输入继续规划 `check` / `distill` 接入。

## Acceptance Criteria

- `run-agents` 结果中存在稳定的结构化阶段合同字段。
- 现有 `agent_runs` 行为保持兼容。
- 文档、CLI 测试、integration 测试同步更新。
- 本轮不依赖宿主模型也能完整跑通阶段合同协议。

## Exception Handling

- 如果实现过程中发现现有字段不足以兼容旧调用方，优先加字段而不是替换旧字段。
- 如果阶段合同无法从现有事实直接推导，必须保留 `unknown` / 空列表等稳定值，不能伪造确定性内容。
- 如果新增行为会破坏现有 `run-agents` CLI 使用方式，必须先回退到兼容方案。

## Verification

- 运行 `pytest tests/test_cli.py tests/test_integration.py`
- 检查 `run-agents --json` 输出中 `agent_runs` 与新阶段合同字段是否并存
- 检查 verify 缺失 / 非 PASS / summary 缺失时是否分别体现阻断或 fallback 事实

## References

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/PLANS.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/design-docs/harness-engineering.md`
- `docs/product-specs/v2/index.md`
- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`
