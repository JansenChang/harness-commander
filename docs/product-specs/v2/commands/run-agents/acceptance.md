# V2 `run-agents` 验收定义

## 当前状态

- active（Phase 2 implementation slice）

## 验收范围

- 验收当前实现切片：
  - 六阶段固定顺序
  - 四槽位协作：`requirements` / `plan` / `implement` / `verify`
  - Harness 独占：`check` / `pr-summary`
  - `requirements` / `plan` host-first 与 fallback
  - verify 阻断与 `pr-summary` fallback
- 不验收并发 runtime、`distill` 联动和恢复机制。

## 验收前提

- 仓库具备最小治理文档
- 输入 spec 与 active plan 可被正常解析
- 运行入口：`harness run-agents --json ...`
- verify 相关用例可控制：
  - `.claude/tmp/last-verify.status`
  - `.claude/tmp/verification-summary.md`

## 验收标准

### AC1 阶段 ownership 固定

- 阶段顺序必须是：`check -> requirements -> plan -> implement -> verify -> pr-summary`
- `check` 与 `pr-summary` 的 `host_model_allowed=false`
- `requirements` 与 `plan` 的 `host_model_allowed=true`
- `implement` 与 `verify` 必须存在于阶段合同中，但当前切片 `host_model_allowed=false`
- `meta.agent_runs` 与 `meta.stage_contracts` 描述同一执行事实

### AC2 最小闭环成功

- 当 `check=success`
- 且 `requirements` / `plan` 能产出合法阶段结果
- 且 `implement` 成功形成实施摘要
- 且 verify 为 PASS
- 则命令结果必须为 `success`
- 且必须生成 `pr-summary` 产物

### AC3 preflight 阻断有效

- `check.failure` 必须阻断四个协作槽位和 `pr-summary`
- `check` 缺少必要治理字段时必须按保守策略直接 `failure`
- `check.warning` 必须允许继续，但 warning 必须进入最终结果

### AC4 `requirements` / `plan` host fallback 可解释

- provider 被策略禁用时：
  - 不尝试 host path
  - deterministic 路径成功时阶段可为 `success`
  - 必须留下 skipped-host-path 事实
- provider 缺失、不可用、超时、空结果或结构不完整时：
  - 必须回退 deterministic
  - 对应阶段至少为 `warning`
  - 命令最终至少为 `warning`
- host-path 失败且 deterministic fallback 仍不能产出最小合同：
  - 命令必须为 `failure`

### AC5 verify 阻断语义稳定

- verify 文件缺失或 verify 非 PASS 时：
  - `verify` 阶段必须为 `warning`
  - `pr-summary` 必须被阻断
  - 命令结果必须为 `warning`
  - 必须给出稳定 `verify_not_ready_for_pr` warning code

### AC6 `pr-summary` fallback 语义稳定

- verify 为 PASS 但 verification summary 缺失或为空时：
  - `pr-summary` 仍可生成
  - `pr-summary.fallback.applied=true`
  - 生成内容必须包含 fallback 痕迹
  - 不得伪造完整 verification summary

### AC7 结果一致性

- 文本 summary、JSON 结果、warning / error code、结构化阶段合同和文件产物必须共享同一份事实
- 不允许出现“结果写 success，但 `pr-summary` 实际被 verify 阻断”的漂移

## 最小闭环验收步骤

1. 执行成功路径，确认六阶段完整、四槽位协作可见、`pr-summary` 生成。
2. 执行 `check=failure` 路径，确认四个协作槽位都不进入。
3. 执行 `check=warning` 路径，确认命令继续且 warning 留痕。
4. 执行 provider 缺失或不可用路径，确认 `requirements` / `plan` fallback 为 `warning` 且命令最终至少 `warning`。
5. 执行 provider 被策略禁用路径，确认 deterministic 成功且保留 skipped-host-path 事实。
6. 执行 verify 缺失路径，确认 `pr-summary` 被阻断。
7. 执行 verify 非 PASS 路径，确认 `pr-summary` 被阻断。
8. 执行 verify 为 PASS 但 summary 缺失路径，确认 `pr-summary` fallback 生成。
9. 比对 `meta.agent_runs` 与 `meta.stage_contracts` 的阶段序列和状态一致性。

## 判定规则

- 任一 AC 不满足，则本轮 Phase 2 实现切片验收不通过。
- 仅当最小闭环、主要失败路径、verify 阻断和 fallback 语义都通过时，才可进入下一轮扩展。
- 若实现需要扩大到 `implement` / `verify` 的宿主模型参与，必须新开 active plan，而不是在本轮验收中顺带放行。

## 非目标

- 不验收并发 agent runtime
- 不验收 `distill` 联动
- 不验收 resume / retry / attempt 机制
- 不验收新的 CLI 模式门
