# 2026-04-06 Harness-Commander V1 总计划

## Goal

- 基于按命令拆分的产品规格，推进 Harness-Commander V1 的后续实现与维护。
- 让产品文档、执行计划和上下文引用方式都与实际命令执行顺序一致。

## Context

- 当前活跃规格已改为 `docs/product-specs/v1/commands/` 按命令维护。
- 当前活跃计划已改为 `docs/exec-plans/active/harness-commander-v1/` 按命令维护。
- `init` 作为已实现基线保留，但不作为本轮主要扩写对象。

## 命令计划入口

- `propose-plan`：`docs/exec-plans/active/harness-commander-v1/propose-plan.md`
- `plan-check`：`docs/exec-plans/active/harness-commander-v1/plan-check.md`
- `sync`：`docs/exec-plans/active/harness-commander-v1/sync.md`
- `distill`：`docs/exec-plans/active/harness-commander-v1/distill.md`
- `check`：`docs/exec-plans/active/harness-commander-v1/check.md`
- `collect-evidence`：`docs/exec-plans/active/harness-commander-v1/collect-evidence.md`

## Cross-Cutting Rules

- 所有命令继续以仓库根目录为执行基准
- 所有命令必须同时支持文本输出和 `--json`
- 写入型命令必须支持 `--dry-run`
- 宿主模型只能参与产品规格允许的认知型任务

## Verification

- 计划与产品规格的命令边界必须一一对应
- 单独修改某个命令的计划时，不应影响其他命令计划正文

## ULW 1: provider 安装绑定重构

### 目标

- 把 provider 主路径从运行时 `--provider` 改为安装/配置阶段绑定，保证 `distill` 与 `run-agents` 默认读取项目配置。
- 把安装目标从仓库内 Claude 项目级 skill 扩展为按用户本机环境自动适配的多宿主用户级目录安装。

### 涉及范围

- 新增 `install-provider` Python 命令与 `.harness/provider-config.json`。
- 把安装语义升级为：先探测宿主，再解析用户级 skill / command / agent 配置目录，最后按 provider 逐项安装。
- Claude 不再只是通过 Python 主路径安装仓库内 `.claude/skills/harness/SKILL.md`；该项目级产物只作为兼容层保留。
- 明确 `auto` / `all` 语义与 provider 安装规格表，要求覆盖 Claude、Cursor、Codex、OpenClaw、Trae、Copilot。
- 保留 `--provider` 作为临时 override，并补齐测试与文档。

### 验收标准

- `distill` 的 `host-model` / `auto` 模式默认读取项目配置 provider。
- `run-agents` 默认读取项目配置 provider，显式 `--provider` 可覆盖。
- `install-provider --provider claude|auto|all` 能落盘配置并返回稳定 JSON 结果。
- `install-provider --provider auto|all` 会按探测结果自动适配用户机器上的 Claude、Cursor、Codex、OpenClaw、Trae、Copilot 等宿主，而不是只安装 Claude。
- `install-provider` 的结果中必须包含每个 provider 的目标目录解析、安装模式与真实产物路径；`--dry-run` 只返回产物预览，不真实落盘。
- 项目级 `.claude/skills/harness/SKILL.md` 只作为兼容安装层，不再是默认唯一落点。
- 文档、计划、测试与实现对齐新的 provider 解析优先级与多宿主安装语义。
