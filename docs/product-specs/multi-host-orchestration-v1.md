# Harness-Commander 多宿主与多 agent 编排 V1

## 1. 业务目标

- 解决当前仓库实现层基本只围绕 Claude 的问题。
- 让 Harness-Commander 在产品层正式支持 Cursor、Claude、Codex、OpenClaw、Trae、Copilot 六类宿主工具 provider。
- 提供一个按当前 product spec 与 active exec plan 顺序推进的多 agent 工作流，减少宿主工具直接自由发挥导致的漂移。

## 2. 核心逻辑

- Harness 继续负责命令语义、输入约束、输出结构、产物路径与最终状态。
- provider 负责宿主工具 CLI 差异，不负责决定通过/失败语义。
- provider 主路径改为安装/配置阶段绑定；运行时默认读取项目级配置，`--provider` 仅作为临时 override。
- `run-agents` 首版采用顺序阶段编排，而不是并发 runtime。
- active exec plan 继续以 `docs/exec-plans/active/` 下的 Markdown 作为事实源。
- `verify` 阶段必须读取现有 `.claude/tmp/last-verify.status` 与 `.claude/tmp/verification-summary.md`，验证未通过时不得进入 PR 整理。

## 3. 首版能力范围

- `distill` 支持 `--provider`。
- `run-agents` 支持 `--spec`、`--plan`、`--provider`、`--dry-run`。
- `run-agents` 固定阶段为：requirements、plan、implement、verify、pr-summary。
- 生成最小 PR summary 到 `docs/generated/pr-summary/`。

## 4. 非目标

- 不在首版引入并发 orchestrator。
- 不在首版把 active exec plan 改为结构化新格式。
- 不在首版为所有 provider 分别提供完整安装器或 IDE 插件包装层。
