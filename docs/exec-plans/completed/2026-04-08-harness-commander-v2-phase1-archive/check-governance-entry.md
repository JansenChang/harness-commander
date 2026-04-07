# Harness-Commander V2 `check` 治理入口执行计划

## Goal

把 V2 `check` 从“规则扫描器”推进到“治理完整性入口”的第一轮可执行版本，让命令结果不仅能列问题，还能给出稳定的健康度、入口就绪判断和下一步动作建议。

## Context

- V2 已确认 `check` 的正式定位是治理完整性入口。
- 当前 `check` 已能输出阻断项、提醒项和未量化规则，但结果仍偏“问题清单”。
- `run-agents` Phase 1 已落地阶段合同，下一步需要一个更像前置门的治理命令来告诉 agent / 人类“现在该做什么”。
- 本轮仍保持 deterministic baseline，不引入宿主模型参与 `check` 的结果判断。

## Business Logic

- `check` 这轮不扩展成大型知识库扫描器，而是先把结果协议升级成决策输入。
- 命令必须回答三件事：
  - 当前健康度如何
  - 是否适合进入下一步
  - 下一步最应该做什么
- 本轮优先复用现有审计事实，不大幅扩扫描面。
- 结果协议必须保持现有 warning / failure / checks 明细兼容。

## Scope

- 为 `check` 增加健康度和治理入口元数据
- 为 `check` 增加稳定的 `next_actions`
- 更新 V2 `check` 的产品、协议、测试、验收文档
- 补 CLI / integration 覆盖

## Non-Goals

- 不引入宿主模型评分或判定
- 不把 `check` 并入 `run-agents` 自动执行
- 不一次性扩展到所有知识库、版本漂移、引用映射扫描
- 不重写现有阻断 / warning 基础规则

## ULW 1: 锁定治理入口结果协议

### 目标

- 明确 `check` 作为治理入口至少应返回哪些决策字段。

### 涉及范围

- `docs/product-specs/v2/commands/check/product.md`
- `docs/product-specs/v2/commands/check/protocol.md`
- `src/harness_commander/application/commands.py`

### 验收标准

- 结果至少新增：
  - `health_score`
  - `governance_entry`
  - `next_actions`
- `governance_entry` 至少明确：
  - 当前入口状态
  - 是否可进入 `run-agents`
  - 是否已达到“无提醒”状态
  - 推荐下一步入口

## ULW 2: 让审计结果变成下一步动作输入

### 目标

- 把现有 issue 列表整理成稳定、可执行的行动建议。

### 涉及范围

- `src/harness_commander/application/commands.py`
- `tests/test_cli.py`
- `tests/test_integration.py`

### 验收标准

- blocking 场景时，`next_actions` 先返回阻断修复动作。
- warning-only 场景时，`next_actions` 返回最合理的推进建议。
- 没有问题时，结果能明确说明当前可继续推进。

## ULW 3: 保持兼容并补齐覆盖

### 目标

- 在增强结果协议的同时，保持现有 `check` 输出兼容。

### 涉及范围

- `tests/test_cli.py`
- `tests/test_integration.py`
- `docs/product-specs/v2/commands/check/testing.md`
- `docs/product-specs/v2/commands/check/acceptance.md`

### 验收标准

- 保持现有：
  - `blocking_count`
  - `warning_count`
  - `checks`
  - `checked_targets`
- 新增覆盖：
  - blocking 时的治理入口状态
  - warning-only 时的治理入口状态
  - 默认目标缺失时的推荐下一步

## ULW 4: 为后续接入 `run-agents` / `distill` 留扩展位

### 目标

- 让 `check` 的结果协议可以在下一轮被 `run-agents` 或其他命令消费。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/product-planning.md`
- `docs/exec-plans/tech-debt-tracker.md`
- `docs/design-docs/harness-engineering.md`

### 验收标准

- 当前结果协议不依赖宿主模型才能成立。
- 后续若要把 `check` 变成真正前置门，不需要再推翻本轮字段。
- 若本轮只实现了“结果层治理入口”，台账中有明确留痕。

## Acceptance Criteria

- `check` 返回稳定的治理入口元数据。
- 审计结果能直接给出下一步动作，而不是只给问题列表。
- 现有结果字段保持兼容。
- 文档、代码、测试同步更新。

## Exception Handling

- 如果现有 issue 无法可靠映射到动作建议，必须返回保守动作，不得伪造确定性建议。
- 如果健康度无法精确表达真实风险，优先让它成为启发式指标，不能替代 blocking / warning 真相。
- 如果新增字段会破坏现有调用方，优先附加字段，不替换旧字段。

## Verification

- 运行 `pytest tests/test_cli.py tests/test_integration.py -k check`
- 检查 blocking / warning / success 三类场景的 `health_score`、`governance_entry`、`next_actions`
- 检查现有 `checks`、`checked_targets`、count 字段是否仍保留

## References

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/PLANS.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/design-docs/harness-engineering.md`
- `docs/product-specs/v2/index.md`
- `docs/product-specs/v2/commands/check/product.md`
