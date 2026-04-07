# Harness-Commander V1 按命令执行计划索引

## 说明

- 本目录按命令拆分维护 Harness-Commander V1 当前仍需跟进的执行计划。
- 命令级计划与 `docs/product-specs/v1/commands/` 保持一一对应，便于只更新当前命令的实现上下文。
- 本文件是当前 active 计划主入口；历史阶段计划与已完成事项应迁入 `docs/exec-plans/completed/`。
- `init` 已作为实现基线落地，当前不再作为主要 active 开发项。

## 开发进度快照（2026-04-07）

| 命令 | 状态 | 备注 |
| --- | --- | --- |
| `propose-plan` | 已实现 | 保留计划作为结构与约束的维护入口 |
| `plan-check` | 已实现 | 保留计划作为规则收敛入口 |
| `sync` | 已实现 | 保留计划作为重大变更与产物更新维护入口 |
| `distill` | 已实现 | 已有可选宿主模型增强，继续维护结果协议 |
| `install-provider` | 已实现，继续硬化 | 当前重点在用户目录安装、权限失败语义和验收覆盖 |
| `check` | 已实现 | 当前重点在默认扫描范围与规则来源稳定性 |
| `collect-evidence` | 已实现 | 作为统一留痕入口继续保留 |
| `run-agents` | 已实现，继续硬化 | 当前重点在验证阻断、provider 默认解析和 PR summary 产物 |

## 计划入口

- `propose-plan`：`propose-plan.md`
- `plan-check`：`plan-check.md`
- `sync`：`sync.md`
- `distill`：`distill.md`
- `install-provider`：`install-provider.md`
- `check`：`check.md`
- `collect-evidence`：`collect-evidence.md`
- `run-agents`：`run-agents.md`
