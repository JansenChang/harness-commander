# `harness run-agents` 测试标准

- 必测：`--json`、`--dry-run`、provider 参数、缺失 spec、缺失 plan、计划校验失败、验证未通过时阻断 PR summary、验证通过时生成 PR summary。
- 必测：`meta.agent_runs[]` 包含 requirements、plan、implement、verify；验证通过时额外包含 pr-summary。
- 必测：输出文本与 JSON 状态一致，不伪造 verify 成功。
- 通过标准：阶段顺序稳定、产物路径固定、provider 元信息稳定、阻断逻辑可解释。
