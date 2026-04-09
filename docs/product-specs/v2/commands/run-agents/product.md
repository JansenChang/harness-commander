# V2 `run-agents` 产品定义

## 当前状态

- phase1-complete / phase2-implementation-slice

## V2 定位

- `run-agents` 是 V2 的治理主入口，不是附属工具命令。
- `run-agents` 的目标形态不是并发 agent runtime，而是一个由 Harness 编排的顺序协作工作流。
- 该工作流采用“四角色 / 四槽位协作”口径：
  - `requirements`
  - `plan`
  - `implement`
  - `verify`
- `check` 与 `pr-summary` 不属于可替换协作槽位，而是 Harness 独占的治理门与收尾门。
- 当前切片先把阶段合同落地到结果协议，优先收敛 deterministic baseline。
- 本轮不扩并发 runtime，不扩 provider 生命周期，不把外围命令全量并入主链。

## 当前实现切片（Phase 2 implementation slice）

- 顺序阶段升级为：`check -> requirements -> plan -> implement -> verify -> pr-summary`。
- 上述顺序中，真正承担协作工作的只有四个槽位：
  - `requirements`：需求澄清槽位
  - `plan`：方案规划槽位
  - `implement`：实现承接槽位
  - `verify`：验证承接槽位
- `check` 由 Harness 独占执行，作为进入四槽位之前的治理前置门。
- `pr-summary` 由 Harness 独占执行，作为离开四槽位后的收尾产物门。
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
- 四槽位按固定顺序串行执行，不引入并发 runtime 或多 agent 调度器。
- 阶段执行事实由 Harness 决定，不能由模型覆盖。
- 结构化合同优先于自由文本摘要。
- 所有状态结论必须来自本地可验证事实（计划校验、verify 文件状态、落盘结果）。

## 宿主模型策略（本轮）

- 本轮暂不启用宿主模型主路径。
- 为后续阶段预留边界：
  - 四槽位中，只有 `requirements`、`plan` 后续可切到“默认优先宿主模型，失败 fallback”。
  - `implement`、`verify` 继续保留为非宿主模型槽位。
  - `check`、`pr-summary` 永远由 Harness 独占控制。
  - `verify`、最终状态、阻断逻辑、产物路径与命名永远由 Harness 控制。

## Phase 2 当前规划方向

- 进入“默认优先宿主模型，失败 fallback”模式时，只开放四槽位中的 `requirements` 与 `plan`。
- Harness 继续负责：
  - `check` preflight 消费
  - `pr-summary` 生成
  - verify 判定
  - 最终状态
  - 结构化阶段合同
- 当前 Phase 2 implementation slice 已落地代码与测试，但仍未扩展到真实并发 runtime 或新的宿主模型 runtime。

## Phase 2 当前已锁定决策

- `run-agents` 统一采用“四角色 / 四槽位协作 + Harness 独占 check / pr-summary”的产品口径。
- 四槽位固定为：`requirements -> plan -> implement -> verify`；它们是顺序协作槽位，不代表并发 runtime。
- `check` 是进入四槽位前的 Harness 独占治理门；`pr-summary` 是离开四槽位后的 Harness 独占收尾门。
- Phase 2 不新增新的 CLI 模式门；`run-agents` 对 `requirements` / `plan` 采用“默认评估 host-first 资格”的策略。
- 只有当 provider 已配置、已启用且当前可用时，`requirements` / `plan` 才进入宿主模型主路径。
- provider 缺失或运行时不可用时，`requirements` / `plan` 必须回退到 deterministic 路径，并留下显式 fallback 事实。
- provider 被策略禁用时，不尝试宿主模型，但仍可直接走 deterministic 路径；该事实必须结构化留痕，不应伪装成 host-path 成功。
- `requirements` / `plan` 在 Phase 2 继续输出结构化摘要，不升级为可重放任务包。
- 只要发生 host-path 失败后 fallback 成功，该阶段至少为 `warning`；命令级结果也至少为 `warning`。
- `check`、`implement`、`verify`、`pr-summary` 继续保持 `host_model_allowed=false`。
- 无论宿主模型是否参与，最终状态、verify 门禁、阻断逻辑、产物路径与 fallback 记录仍只由 Harness 控制。

## 永不交给宿主模型的能力

- `check` 执行权
- `verify` 通过判断
- `pr-summary` 生成前置门禁
- `pr-summary` 生成执行权
- 阶段顺序与最终 `CommandResult`
- 产物路径和命名
- fallback 是否发生及其记录方式

## 与 active exec plan 对齐

- Phase 1 已归档：
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive/run-agents-stage-contracts.md`
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive/run-agents-check-preflight.md`
- Phase 2 主计划参考：
  - `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- Phase 2 当前实现切片归档：
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase2-implementation-slice-archive.md`
- Phase 2 命令级计划参考：
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
- 不把四槽位扩成可恢复 / 可抢占 / 可重排的调度系统

## 当前开放问题

- `docs` 是否应该成为正式 runtime 阶段？
- 后续是否在阶段合同上增加 resume token / attempt 序号？
- `run-agents` 与 `check` 的前置门关系是否要升级为强约束？
