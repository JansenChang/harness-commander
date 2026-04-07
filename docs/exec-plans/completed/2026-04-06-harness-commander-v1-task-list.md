# 2026-04-06 Harness-Commander V1 实现任务清单

## 使用说明

- 本清单基于 `docs/exec-plans/active/harness-commander-v1/` 下的命令级计划拆分。
- 目标是把每个命令拆成可直接开工的实现任务，减少再次解释上下文的成本。
- `init` 属于已实现基线，不作为本轮主要开发任务。

## 命令任务入口

- `propose-plan`：`docs/exec-plans/active/harness-commander-v1/propose-plan.md`
- `plan-check`：`docs/exec-plans/active/harness-commander-v1/plan-check.md`
- `sync`：`docs/exec-plans/active/harness-commander-v1/sync.md`
- `distill`：`docs/exec-plans/active/harness-commander-v1/distill.md`
- `check`：`docs/exec-plans/active/harness-commander-v1/check.md`
- `collect-evidence`：`docs/exec-plans/active/harness-commander-v1/collect-evidence.md`

## 交付检查表

- 每个命令都有独立计划入口
- 每个命令都能单独维护产品/协议/测试/验收上下文
- 所有写入型命令都覆盖 `--dry-run`
- 所有命令都覆盖统一 JSON 输出
- 宿主模型参与点仅出现在产品规格允许的认知型任务中
- provider 默认解析优先级固定为：override > default_provider > installed_providers
- 已补充 `install-provider` 的产品/协议/测试/验收文档
- `install-provider` 本轮实现方向：优先解析并安装到用户本机宿主目录，项目级 `.claude/skills/` 只保留兼容层
- `auto` / `all` 必须覆盖 Claude、Cursor、Codex、OpenClaw、Trae、Copilot 等宿主，逐项返回探测目录、安装模式与失败原因
