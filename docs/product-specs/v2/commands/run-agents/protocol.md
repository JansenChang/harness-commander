# V2 `run-agents` 协议定义

## 当前状态

- phase1-complete / phase2-implementation-slice

## 结果协议总览

- 命令结果保留兼容字段：`meta.agent_runs`
- 命令结果新增结构化字段：`meta.stage_contracts`
- 两者必须指向同一执行事实，不允许出现文本与结构化字段漂移

## 四角色 / 四槽位协作模型

- `run-agents` 的协作主体固定为四个顺序槽位：
  - `requirements`
  - `plan`
  - `implement`
  - `verify`
- `check` 与 `pr-summary` 不属于协作槽位：
  - `check` 是 Harness 独占的前置治理门
  - `pr-summary` 是 Harness 独占的收尾产物门
- 四槽位是顺序合同，不代表并发 runtime、任务抢占或多 agent 调度。

## 阶段合同字段（最小集）

每个阶段必须输出以下字段：

- `stage`: 阶段名
- `status`: `success` / `warning` / `failure`
- `inputs`: 阶段输入来源与关键参数
- `outputs`: 阶段输出摘要与关键结构
- `blocking_conditions`: 阶段阻断条件及命中状态
- `fallback`: 是否 fallback、fallback 来源与原因
- `artifacts`: 阶段产物列表（路径、类型、动作）
- `host_model_allowed`: 当前阶段是否允许宿主模型参与

## 当前阶段定义（deterministic baseline）

### `check`

- `host_model_allowed`: `false`
- 角色：Harness 独占前置治理门
- 输入：当前输入计划上下文 + `check` 治理预检执行结果
- 输出：治理摘要（如 `health_score`、`governance_entry`、`next_actions`）的结构化镜像
- 阻断：
  - `check.status=failure` -> 命令级 `failure`，后续阶段不进入
  - `check` 结果缺失必要治理字段 -> 保守阻断为命令级 `failure`
- fallback：无
- 产物：无

### `requirements`

- `host_model_allowed`: `true`
- 角色：槽位 1 / 需求澄清
- 输入：spec 解析结果
- 当前执行路径：仍走 deterministic 摘要合同，但保留 host-first 候选事实
- 阻断：spec 文件缺失 -> 命令级 `failure`
- fallback：无
- 产物：无

### `plan`

- `host_model_allowed`: `true`
- 角色：槽位 2 / 方案规划
- 输入：active plan 解析结果 + 治理校验结果
- 当前执行路径：仍走 deterministic 摘要合同，但保留 host-first 候选事实
- 阻断：plan 缺失 / plan 校验不通过 -> 命令级 `failure`
- fallback：无
- 产物：无

### `implement`

- `host_model_allowed`: `false`
- 角色：槽位 3 / 实现承接
- 输入：requirements 与 plan 阶段摘要
- 阻断：无硬阻断（当前仅摘要承接）
- fallback：无
- 产物：无

### `verify`

- `host_model_allowed`: `false`
- 角色：槽位 4 / 验证承接
- 输入：`.claude/tmp/last-verify.status`、`.claude/tmp/verification-summary.md`
- 阻断：
  - `last-verify.status` 缺失 -> `warning`，阻断 `pr-summary`
  - verify 状态非 PASS -> `warning`，阻断 `pr-summary`
- fallback：
  - verification summary 缺失或为空 -> fallback 摘要文案
- 产物：无

### `pr-summary`

- `host_model_allowed`: `false`
- 角色：Harness 独占收尾产物门
- 进入条件：`verify.status == success`
- 阻断：verify 未通过或未就绪
- fallback：无
- 产物：`docs/generated/pr-summary/*.md`（dry-run 为 would_create）

## 宿主模型边界（本轮）

- 当前实现切片中：
  - `requirements` / `plan` 已标记为 `host_model_allowed=true`
  - 但它们当前仍走 deterministic 摘要合同，不直接调用宿主模型
  - `check` / `implement` / `verify` / `pr-summary` 继续保持 `host_model_allowed=false`
- 后续仍仅四槽位中的 `requirements` / `plan` 可评估开启宿主模型主路径。
- 即使后续开启，以下能力继续禁止模型接管：
  - `check` 执行
  - verify 通过判断
  - 阻断逻辑
  - 最终状态
  - `pr-summary` 执行
  - 产物路径与命名

## Phase 2 当前已锁定规则

- `run-agents` 统一采用“四角色 / 四槽位协作 + Harness 独占 check / pr-summary”的协议口径。
- 四槽位固定为 `requirements -> plan -> implement -> verify`，且保持顺序执行。
- `requirements` / `plan` 是 Phase 2 中唯一允许进入宿主模型主路径的槽位。
- `requirements` / `plan` 的宿主模型合同继续保持“结构化摘要”，不升级为可重放任务包。
- `requirements` / `plan` 评估 host-first 的前提是：
  - provider 已配置
  - provider 已启用
  - provider 当前可用
- provider 缺失或运行时不可用时：
  - 不应立即中断命令
  - 必须回退到 deterministic 路径
  - 必须在阶段合同中留下 fallback 事实
- provider 被策略禁用时：
  - 不尝试宿主模型
  - 可直接走 deterministic 路径
  - 必须在结构化结果中留下“按策略跳过 host path”的事实
- 宿主模型返回空结果、超时或结构不完整时，必须视为 host-path 失败，不得伪造阶段成功。
- 无论 Phase 2 如何推进，以下阶段继续保持 `host_model_allowed=false`：
  - `check`
  - `implement`
  - `verify`
  - `pr-summary`
- 当前实现切片归档：
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase2-implementation-slice-archive.md`
- 命令级计划参考：
  - `docs/exec-plans/active/harness-commander-v2/run-agents-host-model-phase2-contracts.md`

## Phase 2 阶段输入输出要求

当槽位 1 / 2（`requirements` / `plan`）进入宿主模型主路径时，阶段输出仍应保持结构化摘要合同，最小应能表达：

- `summary`
- `source_inputs`
- `key_decisions`
- `open_questions`
- `handoff_notes`
- `execution_path`
- `host_attempted`

这些字段可以由 `outputs` 承载，但最终阶段状态、blocking 与 fallback 事实仍由 Harness 写入。

`implement` 与 `verify` 继续消费前序槽位的结构化摘要，不升级为新的宿主模型输入包格式。

## 失败与回退语义

- 命令级 `failure`：
  - `check` 预检失败
  - `check` 缺失必要治理字段（保守阻断）
  - spec 缺失
  - plan 缺失
  - plan 校验失败
  - 宿主模型失败且 deterministic fallback 也无法产出合法阶段结果
- 命令级 `warning`：
  - `check.status=warning`，并继续进入 requirements
  - verify 缺失或非 PASS，`pr-summary` 阶段被阻断
  - `requirements` / `plan` 发生 host-path 失败后 fallback 成功
- fallback 语义：
  - verify summary 缺失时，必须保留 fallback 事实，不得伪造完整验证摘要
  - 槽位 1 / 2（`requirements` / `plan`）发生 host-path 退化时，必须保留 provider、原因、是否尝试过 host path 与最终执行路径

## Phase 2 状态矩阵

- 槽位 1 / 2（`requirements` / `plan`）host-path 成功且结构完整：
  - 阶段 `success`
- provider 被策略禁用且 deterministic 路径成功：
  - 阶段 `success`
  - 但必须保留 host path 被策略跳过的事实
- provider 缺失、provider 不可用、宿主模型超时、宿主模型空结果、宿主模型结构不完整，且 deterministic fallback 成功：
  - 阶段 `warning`
  - 命令最终至少 `warning`
- 宿主模型失败且 deterministic fallback 也无法满足阶段最小合同：
  - 阶段 `failure`
  - 命令 `failure`

## 阶段顺序与门禁规则（本轮）

- 固定顺序：`check -> requirements -> plan -> implement -> verify -> pr-summary`
- 其中 `check` / `pr-summary` 为 Harness 独占门，四槽位仅指中间的 `requirements -> plan -> implement -> verify`。
- 前置门语义：
  - `check=failure`：立即结束，`requirements` 及后续阶段不得出现成功执行事实
  - `check=warning`：继续执行，但 warning 必须进入 `meta.agent_runs` 与 `meta.stage_contracts`
  - `check=success`：正常继续
