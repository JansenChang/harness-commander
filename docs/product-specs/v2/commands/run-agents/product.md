# V2 `run-agents` 产品定义

## 当前状态

- phase1-complete / phase2-planning

## V2 定位

- `run-agents` 是 V2 的治理主入口，不是附属工具命令。
- 当前切片先把阶段合同落地到结果协议，优先收敛 deterministic baseline。
- 本轮不扩并发 runtime，不扩 provider 生命周期，不把外围命令全量并入主链。

## 当前实现切片（Phase 1）

- 顺序阶段升级为：`check -> requirements -> plan -> implement -> verify -> pr-summary`。
- `check` 作为治理前置门（preflight）：
  - `check.failure`：阻断后续全部阶段，命令级 `failure`。
  - `check.warning`：允许继续进入 requirements，但必须在结果中显式留痕。
  - `check.success`：正常继续。
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

## Phase 2 当前规划方向

- 进入“默认优先宿主模型，失败 fallback”模式时，只开放 `requirements` 与 `plan`。
- Harness 继续负责：
  - `check` preflight 消费
  - verify 判定
  - 最终状态
  - 结构化阶段合同
- 当前 Phase 2 仍处于产品规划中，未进入实现。

## 永不交给宿主模型的能力

- `verify` 通过判断
- `pr-summary` 生成前置门禁
- 阶段顺序与最终 `CommandResult`
- 产物路径和命名
- fallback 是否发生及其记录方式

## 与 active exec plan 对齐

- Phase 1 已归档：
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive/run-agents-stage-contracts.md`
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive/run-agents-check-preflight.md`
- 当前 Phase 2 主计划：
  - `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- 当前 Phase 2 命令级计划：
  - `docs/exec-plans/active/harness-commander-v2/run-agents-host-model-phase2-contracts.md`
- 对齐 ULW：
  - ULW 1：阶段合同字段收敛
  - ULW 2：合同进入结果协议且保持兼容
  - ULW 3：覆盖 `check` preflight 三态（failure 阻断 / warning 继续 / success 继续）
  - ULW 4：为后续强前置门与 `distill` 接入留稳定扩展位

## 当前非目标

- 不引入并发 agent runtime
- 不把 `collect-evidence`、`distill` 强行并入主链执行
- 不在本轮切宿主模型默认主路径

## 当前开放问题

- `docs` 是否应该成为正式 runtime 阶段？
- 后续是否在阶段合同上增加 resume token / attempt 序号？
- `run-agents` 与 `check` 的前置门关系是否要升级为强约束？
- `requirements` / `plan` 的宿主模型输出是否要升级为可重放任务包格式？
