# Harness-Commander 应用层命令重构计划

## Goal

在不改变现有产品逻辑、结果协议和 CLI 参数的前提下，把 `src/harness_commander/application/commands.py` 从 2400+ 行单体模块重构为可维护的分层命令结构，并建立后续开发规范。

## Context

- 当前 `commands.py` 已承载：
  - 多个命令入口
  - sync / distill / check / run-agents 的大量私有辅助函数
  - provider 安装与 fallback 编排
- 这已经偏离 `ARCHITECTURE.md` 中“应用层保留命令入口边界”的目标。
- 当前 V2 仍停留在产品规划阶段，尚未开始 Phase 2 实现切片。
- 因此本轮最合理的工程动作不是继续堆 Phase 2 实现，而是先治理应用层结构。

## Business Logic

- 这轮重构是工程治理，不是产品扩 scope。
- 重构成功的标准不是“文件拆开了”，而是：
  - 公共入口兼容
  - 测试继续通过
  - 新增开发规范可以约束后续实现不再回退成单体模块
- 在本计划完成前，Phase 2 继续停留在产品/协议收敛，不进入实现。

## Scope

- 为应用层命令实现建立正式开发规范
- 把 `commands.py` 降级为 façade + 兼容导出层
- 将命令实现拆入 `application/command_handlers/`
- 保持现有 CLI、结果协议、产物路径与测试语义稳定

## Non-Goals

- 不修改任何命令的产品逻辑
- 不扩展新的命令参数
- 不改变宿主模型参与边界
- 不顺手推进 V2 Phase 2 的功能实现
- 不重写 CLI 层或 domain 层协议

## ULW 1: 锁定应用层开发规范

### 目标

- 把“`commands.py` 不得继续膨胀”的规则写成仓库事实源。

### 涉及范围

- `docs/design-docs/application-command-development.md`
- `docs/design-docs/index.md`
- `ARCHITECTURE.md`

### 验收标准

- 明确 `commands.py` 只作为 façade 的定位
- 明确命令模块拆分策略、共享逻辑抽取条件与复杂度上限
- 明确当前重构完成前，不进入 Phase 2 实现切片

## ULW 2: 拆分应用层命令模块

### 目标

- 让命令实现按职责进入独立模块，同时保持公共导出面兼容。

### 涉及范围

- `src/harness_commander/application/commands.py`
- `src/harness_commander/application/command_handlers/`

### 验收标准

- `commands.py` 只保留统一异常收敛与公共导出包装
- `distill`、`check`、`run-agents` 至少完成独立模块拆分
- 共享但稳定的辅助逻辑进入命令子模块或共享 helper，而不是继续堆在 façade

## ULW 3: 锁定重构期间的兼容性

### 目标

- 避免因为文件拆分导致 CLI、测试 patch 点或结果合同漂移。

### 涉及范围

- `src/harness_commander/cli.py`
- `tests/test_cli.py`
- `tests/test_integration.py`

### 验收标准

- 现有 CLI 调用方式不变
- 现有关键 patch 点保持可用，或有等价兼容层承接
- `CommandResult`、JSON 输出和 artifact 事实不发生行为回归

## ULW 4: 用测试锁住结构治理结果

### 目标

- 把本轮结构治理变成稳定基线，而不是一次性手工整理。

### 涉及范围

- `tests/test_cli.py`
- `tests/test_integration.py`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`

### 验收标准

- 至少完成 CLI 与 integration 全量回归
- 若补了新的兼容包装或依赖注入点，要有对应测试覆盖
- 若保留临时兼容层或已知限制，要在文档或技术债中留痕

## Acceptance Criteria

- `commands.py` 不再是 2400+ 行单体模块。
- 应用层命令结构与 `ARCHITECTURE.md`、开发规范一致。
- 重构后仓库可明确以该结构为基础继续推进 V2，而不是再次回到单文件堆逻辑。

## Verification

- 运行 `pytest tests/test_cli.py tests/test_integration.py`
- 如涉及 provider 安装公共入口，再运行：
  - `pytest tests/test_provider_install_modes.py tests/test_provider_path_resolution.py`
- 抽查 CLI 命令、JSON 输出与产物路径是否和重构前一致

## 当前落实状态

- 已完成：
  - 应用层命令开发规范落到 `docs/design-docs/application-command-development.md`
  - `commands.py` 降级为 façade + 兼容包装层
  - 命令实现拆入 `application/command_handlers/`
  - 保留 `run_check`、`distill_with_host_model`、`utc_timestamp_precise` 等关键 patch 兼容入口
- 当前结果：
  - `src/harness_commander/application/commands.py` 已降到 250 行以内
  - V2 的后续实现可基于分层后的应用层结构继续推进
- 已验证：
  - `pytest tests/test_cli.py tests/test_integration.py tests/test_provider_install_modes.py tests/test_provider_path_resolution.py`

## References

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/design-docs/application-command-development.md`
- `docs/exec-plans/active/harness-commander-v2/index.md`
