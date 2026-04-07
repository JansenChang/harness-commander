# `harness run-agents` 验收标准

- 成功路径：在有效的 product spec、active exec plan、验证状态为 PASS 的前提下，返回 success，并生成 `docs/generated/pr-summary/*.md`。
- 阻断路径：当验证状态文件缺失、状态非 PASS 或计划校验失败时，不得生成 PR summary；结果必须返回 warning 或 failure，并说明原因。
- `--dry-run`：返回将创建的 PR summary 产物描述，但不实际写入。
- provider 支持：默认应读取项目已配置 provider；`--provider` 作为临时 override 时必须接受 `cursor`、`claude`、`codex`、`openclaw`、`trae`、`copilot`，不支持的值必须返回明确错误。
- 结果协议：`meta.agent_runs[]` 必须保留阶段顺序、provider 和摘要，`meta.provider_source` 必须说明 provider 来源，文本输出与 JSON 输出保持一致。
