# 2026-04-07 V1 开发进度统一与归档记录

## 背景

- active 目录中同时存在历史阶段总计划、过渡任务清单和按命令拆分的 V1 计划，导致当前实现状态与计划入口不一致。
- 当前代码已经实现 `init`、`propose-plan`、`plan-check`、`sync`、`distill`、`check`、`collect-evidence`、`run-agents`、`install-provider`，但计划文档仍保留大量“待实现”语义。

## 本次整理动作

- 更新 `docs/PLANS.md`，把当前统一进度、命令状态和验证阻塞收敛成单一事实来源。
- 为 `install-provider`、`run-agents` 补齐独立命令级 active 计划，去掉对旧总计划的依赖。
- 将历史阶段总计划与过渡任务清单从 `docs/exec-plans/active/` 迁入 `docs/exec-plans/completed/`。

## 本次归档对象

- `docs/exec-plans/active/2026-04-04.md`
- `docs/exec-plans/active/2026-04-04-phase2.md`
- `docs/exec-plans/active/2026-04-06-harness-commander-v1-plan.md`
- `docs/exec-plans/active/2026-04-06-harness-commander-v1-task-list.md`

## 当前状态结论

- V1 命令主链路已从“规划阶段”进入“维护与硬化阶段”。
- active 目录当前应聚焦命令级维护计划，而不是继续承载阶段性总计划。
- `install-provider` 和 `run-agents` 是当前最值得继续保留在 active 的命令级入口，因为它们仍涉及多宿主默认解析、验证阻断、打包安装和真实目录写入等环境相关问题。

## 当前验证快照

- 2026-04-07 本地运行 `pytest`，结果为 `49 passed, 1 failed, 8 errors`。
- 主要阻塞：
  - acceptance 测试中的 editable install 受 PEP 668 限制，`pip install -e .` 在当前环境失败。
  - `install-provider` 的一条测试会触达真实用户目录 `~/.claude/skills/...`，在当前环境下因权限不足失败。

## 后续 active 入口

- `docs/exec-plans/active/harness-commander-v1/index.md`
- `docs/exec-plans/active/harness-commander-v1/install-provider.md`
- `docs/exec-plans/active/harness-commander-v1/run-agents.md`
