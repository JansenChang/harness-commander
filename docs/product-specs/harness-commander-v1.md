# Harness-Commander V1（按命令导航）

## 1. 产品概述

Harness-Commander 是面向研发实现的统一治理入口，用一组固定命令把 AI 开发从需求整理、计划生成、过程同步、约束审计到验证留痕串成同一条生命周期。

V1 的核心目标不是让 Harness 替代 Claude、Cursor、Codex、OpenClaw、Trae、Copilot 等宿主工具，而是让 Harness 统一命令语义、输入约束、输出结构和产物落点；当前默认路径优先保证离线、可测试、可回归，只有明确允许的命令节点才可选接入宿主模型。

## 2. 全局原则

- 命令入口固定为 `harness <command> [options]`
- 所有命令必须同时支持文本输出和 `--json`
- 写入型命令必须支持 `--dry-run`
- 宿主模型只能参与产品文档允许的认知型任务，不能接管结果字段、产物路径和最终状态
- provider 安装默认面向用户本机宿主目录；`auto` 与 `all` 必须按探测结果自动适配 Claude、Cursor、Codex、OpenClaw、Trae、Copilot 等宿主，而不是只围绕 Claude 设计
- 日常维护优先修改对应命令目录下的文档，而不是回到单个大总表里追加章节

## 3. 推荐主流程

`init -> propose-plan -> plan-check -> run-agents -> sync -> distill -> check -> collect-evidence`

## 4. 命令入口

- `init`：[product](./v1/commands/init/product.md) / [protocol](./v1/commands/init/protocol.md) / [testing](./v1/commands/init/testing.md) / [acceptance](./v1/commands/init/acceptance.md)
- `propose-plan`：[product](./v1/commands/propose-plan/product.md) / [protocol](./v1/commands/propose-plan/protocol.md) / [testing](./v1/commands/propose-plan/testing.md) / [acceptance](./v1/commands/propose-plan/acceptance.md)
- `plan-check`：[product](./v1/commands/plan-check/product.md) / [protocol](./v1/commands/plan-check/protocol.md) / [testing](./v1/commands/plan-check/testing.md) / [acceptance](./v1/commands/plan-check/acceptance.md)
- `sync`：[product](./v1/commands/sync/product.md) / [protocol](./v1/commands/sync/protocol.md) / [testing](./v1/commands/sync/testing.md) / [acceptance](./v1/commands/sync/acceptance.md)
- `distill`：[product](./v1/commands/distill/product.md) / [protocol](./v1/commands/distill/protocol.md) / [testing](./v1/commands/distill/testing.md) / [acceptance](./v1/commands/distill/acceptance.md)
- `check`：[product](./v1/commands/check/product.md) / [protocol](./v1/commands/check/protocol.md) / [testing](./v1/commands/check/testing.md) / [acceptance](./v1/commands/check/acceptance.md)
- `collect-evidence`：[product](./v1/commands/collect-evidence/product.md) / [protocol](./v1/commands/collect-evidence/protocol.md) / [testing](./v1/commands/collect-evidence/testing.md) / [acceptance](./v1/commands/collect-evidence/acceptance.md)
- `run-agents`：[product](./v1/commands/run-agents/product.md) / [protocol](./v1/commands/run-agents/protocol.md) / [testing](./v1/commands/run-agents/testing.md) / [acceptance](./v1/commands/run-agents/acceptance.md)

## 5. 测试与验收入口

- 测试标准按命令维护在各命令目录下的 `testing.md`
- 验收标准按命令维护在各命令目录下的 `acceptance.md`
- 当前执行计划见 `docs/exec-plans/active/harness-commander-v1/`
