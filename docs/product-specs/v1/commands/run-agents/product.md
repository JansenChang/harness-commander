# `harness run-agents` 产品定义

## 解决的问题

- 当前实现缺少一个能把 product spec 与 active exec plan 串起来的统一执行入口。
- 宿主工具直接自由执行容易跳过需求、计划、验证与 PR 整理边界。

## 具体作用

- 文档目标阶段模型为 requirements、docs、plan、implement、verify、pr-summary 六个阶段。
- 当前 runtime 仍采用 requirements、plan、implement、verify、pr-summary 五阶段顺序编排；docs 阶段先作为文档与计划层的实现预留。
- 读取产品规格与 active exec plan 的最小结构化信息，生成阶段摘要。
- 复用现有验证状态文件，在验证通过后整理 PR summary。

## 当前实现

- 首版采用顺序阶段编排，不实现并发 runtime。
- provider 首批支持 `cursor`、`claude`、`codex`、`openclaw`、`trae`、`copilot`。
- 默认读取项目已安装/已配置的 provider；显式 `--provider` 仅作为临时 override。
- implement 阶段当前输出实施摘要与执行指令，不接管复杂自动改码 runtime。

## 产物

- `docs/generated/pr-summary/` 下的 PR 摘要文件。
- `CommandResult.meta.agent_runs[]` 中的阶段执行摘要。
