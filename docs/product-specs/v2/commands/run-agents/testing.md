# V2 `run-agents` 测试定义

## 当前状态

- active（Phase 2 implementation slice）

## 测试目标

- 验证 `run-agents` 的 Phase 2 实现切片固定为“四槽位协作 + Harness 独占 check/pr-summary”。
- 验证 `requirements` / `plan` 的 host-first 与 deterministic fallback 语义稳定。
- 验证 verify 阻断、`pr-summary` 生成条件和 verification summary fallback 语义稳定。
- 保持 `meta.agent_runs` 与 `meta.stage_contracts` 指向同一执行事实。

## 当前切片范围

- 固定阶段顺序：`check -> requirements -> plan -> implement -> verify -> pr-summary`
- 四个协作槽位：
  - `requirements`
  - `plan`
  - `implement`
  - `verify`
- Harness 独占阶段：
  - `check`
  - `pr-summary`
- 当前切片仅 `requirements` / `plan` 允许评估 host-first
- `implement` / `verify` 仍以本地可验证事实驱动，不引入新的宿主模型主路径

## 分层策略

- CLI 测试：
  - 校验阶段顺序、结果合同、稳定错误码和 warning code
  - 校验四槽位 / Harness 独占边界在结果协议中可断言
  - 校验 host fallback、verify 阻断和 `pr-summary` fallback 的命令级状态
- Integration 测试：
  - 校验真实文件存在性、落盘行为、路径冲突避让与 dry-run 合同
  - 校验 verify 文件驱动的阶段变化
  - 校验结构化字段、文本 summary 与落盘产物一致

## 测试矩阵

### A. Ownership 与阶段合同

- `check` 固定排在第一阶段，`pr-summary` 固定排在最后阶段。
- `check` 与 `pr-summary` 的 `host_model_allowed` 必须为 `false`。
- `requirements` 与 `plan` 的 `host_model_allowed` 应为 `true`。
- `implement` 与 `verify` 必须作为协作槽位出现，但当前切片 `host_model_allowed=false`。
- `meta.agent_runs` 与 `meta.stage_contracts` 的阶段序列必须一致。

### B. 最小闭环成功路径

- preflight 为 `success`
- `requirements` host-path 成功或 deterministic 路径成功
- `plan` host-path 成功或 deterministic 路径成功
- `implement` 成功产出结构化摘要
- verify 为 PASS，且 verification summary 非空
- 命令结果为 `success`
- 存在 `pr-summary` 产物

### C. preflight 与主失败路径

- `check=failure`
  - 命令 `failure`
  - 四个协作槽位不进入
- `check` 缺少必要治理字段
  - 命令 `failure`
  - 必须返回稳定错误码
- spec 缺失
  - `status=failure`
  - `errors[].code=spec_not_found`
- plan 缺失
  - `status=failure`
  - `errors[].code=plan_not_found`
- plan 校验失败
  - `status=failure`
  - 具备稳定校验错误码

### D. `requirements` / `plan` host fallback

- provider 被策略禁用
  - 不尝试 host path
  - deterministic 路径成功
  - 阶段可为 `success`
  - 必须记录 skipped-host-path 事实
- provider 缺失
  - deterministic fallback 成功
  - 对应阶段 `warning`
  - 命令最终至少 `warning`
- provider 运行时不可用、超时、空结果或结构不完整
  - deterministic fallback 成功
  - 对应阶段 `warning`
  - `fallback.applied=true`
  - 命令最终至少 `warning`
- host-path 失败且 deterministic fallback 也无法满足最小合同
  - 对应阶段 `failure`
  - 命令 `failure`

### E. verify 阻断

- verify 文件缺失
  - `verify.status=warning`
  - `warnings[].code=verify_not_ready_for_pr`
  - `pr-summary` 不生成
- verify 非 PASS
  - `verify.status=warning`
  - 命令 `warning`
  - `pr-summary` 不生成
- verify 阶段合同必须能看见阻断条件命中
- `pr-summary` 阶段合同必须显式反映“因 verify 未就绪而被阻断”

### F. `pr-summary` fallback

- verify 为 PASS，但 verification summary 缺失或为空
  - `pr-summary` 仍可生成
  - `pr-summary.fallback.applied=true`
  - 摘要内容必须明确使用 placeholder / fallback 文案
  - 不得伪造完整 verification summary

### G. 兼容性与一致性

- 保留 `meta.agent_runs` 字段，不改变其基本结构。
- 新增或调整后的阶段合同字段必须可与 `meta.agent_runs` 交叉验证。
- 文本 summary、JSON 结果和文件产物必须反映同一执行事实。

## 最低覆盖要求

- 至少 1 条成功路径
- 至少 1 条主要失败路径
- 至少 1 条边界 / fallback 路径
- 至少 1 条 verify 阻断路径
- 至少 1 条 `pr-summary` fallback 路径

## 建议落点

- `tests/test_cli.py`
  - 锁阶段顺序、状态矩阵、warning / error code 和 dry-run 合同
- `tests/test_integration.py`
  - 锁真实文件行为、verify 文件驱动、路径冲突避让和 artifact 生成

## 非目标测试

- 本轮不测试并发 agent runtime
- 本轮不测试 `distill` 联动编排
- 本轮不测试 resume token / 自动重试 / attempt 编号
- 本轮不测试 `implement` / `verify` 的宿主模型主路径
