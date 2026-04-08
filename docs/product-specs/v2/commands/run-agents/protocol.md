# V2 `run-agents` 协议定义

## 当前状态

- phase1-complete / phase2-planning

## 结果协议总览

- 命令结果保留兼容字段：`meta.agent_runs`
- 命令结果新增结构化字段：`meta.stage_contracts`
- 两者必须指向同一执行事实，不允许出现文本与结构化字段漂移

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
- 输入：当前输入计划上下文 + `check` 治理预检执行结果
- 输出：治理摘要（如 `health_score`、`governance_entry`、`next_actions`）的结构化镜像
- 阻断：
  - `check.status=failure` -> 命令级 `failure`，后续阶段不进入
  - `check` 结果缺失必要治理字段 -> 保守阻断为命令级 `failure`
- fallback：无
- 产物：无

### `requirements`

- `host_model_allowed`: `false`
- 输入：spec 解析结果
- 阻断：spec 文件缺失 -> 命令级 `failure`
- fallback：无
- 产物：无

### `plan`

- `host_model_allowed`: `false`
- 输入：active plan 解析结果 + 治理校验结果
- 阻断：plan 缺失 / plan 校验不通过 -> 命令级 `failure`
- fallback：无
- 产物：无

### `implement`

- `host_model_allowed`: `false`
- 输入：requirements 与 plan 阶段摘要
- 阻断：无硬阻断（当前仅摘要承接）
- fallback：无
- 产物：无

### `verify`

- `host_model_allowed`: `false`
- 输入：`.claude/tmp/last-verify.status`、`.claude/tmp/verification-summary.md`
- 阻断：
  - `last-verify.status` 缺失 -> `warning`，阻断 `pr-summary`
  - verify 状态非 PASS -> `warning`，阻断 `pr-summary`
- fallback：
  - verification summary 缺失或为空 -> fallback 摘要文案
- 产物：无

### `pr-summary`

- `host_model_allowed`: `false`
- 进入条件：`verify.status == success`
- 阻断：verify 未通过或未就绪
- fallback：无
- 产物：`docs/generated/pr-summary/*.md`（dry-run 为 would_create）

## 宿主模型边界（本轮）

- 本轮所有阶段 `host_model_allowed=false`。
- 后续仅 `requirements` / `plan` 可评估开启宿主模型主路径。
- 即使后续开启，以下能力继续禁止模型接管：
  - verify 通过判断
  - 阻断逻辑
  - 最终状态
  - 产物路径与命名

## Phase 2 当前规划问题

- `requirements` / `plan` 若切到默认优先宿主模型：
  - 宿主模型输出是否仍只保留摘要，还是升级为可重放任务包
  - provider 缺失时是直接 failure，还是保守 fallback 到 deterministic 路径
  - 宿主模型返回结构不完整时，如何保留稳定 fallback 事实
- 无论 Phase 2 如何推进，以下阶段继续保持 `host_model_allowed=false`：
  - `check`
  - `verify`
  - `pr-summary`

## 失败与回退语义

- 命令级 `failure`：
  - `check` 预检失败
  - `check` 缺失必要治理字段（保守阻断）
  - spec 缺失
  - plan 缺失
  - plan 校验失败
- 命令级 `warning`：
  - `check.status=warning`，并继续进入 requirements
  - verify 缺失或非 PASS，`pr-summary` 阶段被阻断
- fallback 语义：
  - verify summary 缺失时，必须保留 fallback 事实，不得伪造完整验证摘要

## 阶段顺序与门禁规则（本轮）

- 固定顺序：`check -> requirements -> plan -> implement -> verify -> pr-summary`
- 前置门语义：
  - `check=failure`：立即结束，`requirements` 及后续阶段不得出现成功执行事实
  - `check=warning`：继续执行，但 warning 必须进入 `meta.agent_runs` 与 `meta.stage_contracts`
  - `check=success`：正常继续
