# Harness-Commander 测试标准导航 V1

## 说明

- 命令级测试标准已按命令拆分维护。
- 本文件只保留全局测试目标、测试分层和导航入口。

## 测试目标

- 确认每个命令符合产品定义、命令协议和验收要求。
- 确认不依赖宿主模型时，Harness 核心流程仍可稳定测试。
- 确认涉及宿主模型的命令在无宿主模型、契约返回和本地 Claude 联调三种条件下都有明确测试策略。

## 测试分层

- L1：协议与单元测试
- L2：命令集成测试
- L3：宿主模型契约测试
- L4：本地 Claude 联调测试

## 命令测试入口

- `init`：`docs/product-specs/v1/commands/init/testing.md`
- `propose-plan`：`docs/product-specs/v1/commands/propose-plan/testing.md`
- `plan-check`：`docs/product-specs/v1/commands/plan-check/testing.md`
- `sync`：`docs/product-specs/v1/commands/sync/testing.md`
- `distill`：`docs/product-specs/v1/commands/distill/testing.md`
- `install-provider`：`docs/product-specs/v1/commands/install-provider/testing.md`
- `check`：`docs/product-specs/v1/commands/check/testing.md`
- `collect-evidence`：`docs/product-specs/v1/commands/collect-evidence/testing.md`
- `run-agents`：`docs/product-specs/v1/commands/run-agents/testing.md`

## 执行计划入口

- 当前执行计划：`docs/exec-plans/active/harness-commander-v1/index.md`
