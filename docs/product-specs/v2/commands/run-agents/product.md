# V2 `run-agents` 产品定义

## 当前状态

- active（V2 第一轮实现中）

## V2 定位

- `run-agents` 是 V2 的治理主入口，不是附属工具命令。
- 当前切片先把阶段合同落地到结果协议，优先收敛 deterministic baseline。
- 本轮不扩并发 runtime，不扩 provider 生命周期，不把外围命令全量并入主链。

## 当前实现切片（Phase 1）

- 顺序阶段保持：`requirements -> plan -> implement -> verify -> pr-summary`。
- 输出保持兼容：`meta.agent_runs` 继续保留。
- 新增结构化阶段合同：每个阶段都有统一合同字段，支持后续恢复 / 重试 / 接管。
- verify 缺失或非 PASS 时必须阻断 `pr-summary`，不允许伪造成功。
- verification summary 缺失时允许继续，但必须留下 fallback 事实。

## deterministic baseline（本轮约束）

- 默认不依赖宿主模型。
- 阶段执行事实由 Harness 决定，不能由模型覆盖。
- 结构化合同优先于自由文本摘要。
- 所有状态结论必须来自本地可验证事实（计划校验、verify 文件状态、落盘结果）。

## 宿主模型策略（本轮）

- 本轮暂不启用宿主模型主路径。
- 为后续阶段预留边界：
  - `requirements`、`plan` 后续可切到“默认优先宿主模型，失败 fallback”。
  - `verify`、最终状态、阻断逻辑、产物路径与命名永远由 Harness 控制。

## 永不交给宿主模型的能力

- `verify` 通过判断
- `pr-summary` 生成前置门禁
- 阶段顺序与最终 `CommandResult`
- 产物路径和命名
- fallback 是否发生及其记录方式

## 与 active exec plan 对齐

- 当前执行计划：`docs/exec-plans/active/harness-commander-v2/run-agents-stage-contracts.md`
- 对齐 ULW：
  - ULW 1：阶段合同字段收敛
  - ULW 2：合同进入结果协议且保持兼容
  - ULW 3：成功 / 失败 / fallback 测试覆盖
  - ULW 4：为后续 `check` / `distill` 接入留稳定扩展位

## 当前非目标

- 不引入并发 agent runtime
- 不把 `collect-evidence`、`check`、`distill` 强行并入主链执行
- 不在本轮切宿主模型默认主路径

## 当前开放问题

- `docs` 是否应该成为正式 runtime 阶段？
- 后续是否在阶段合同上增加 resume token / attempt 序号？
- `run-agents` 与 `check` 的前置门关系是否要升级为强约束？
- `requirements` / `plan` 的宿主模型输出是否要升级为可重放任务包格式？
