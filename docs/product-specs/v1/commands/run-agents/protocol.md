# `harness run-agents` 协议

| 项目 | 定义 |
| --- | --- |
| 命令 | `harness run-agents --spec <path> --plan <path>` |
| 参数 | `-p, --root`；`--spec <path>`；`--plan <path>`；`--provider <name>`（临时 override，可选）；`--dry-run` |
| 必填参数 | `--spec`、`--plan` |
| provider | `cursor`、`claude`、`codex`、`openclaw`、`trae`、`copilot` |
| 阶段 | 文档目标模型：`requirements` -> `docs` -> `plan` -> `implement` -> `verify` -> `pr-summary`；当前 runtime：`requirements` -> `plan` -> `implement` -> `verify` -> `pr-summary` |
| 产物落点 | `docs/generated/pr-summary/` |
| JSON `meta` | `root`、`spec_path`、`plan_path`、`provider`、`provider_source`、`supported_providers`、`agent_runs`、`dry_run` |
| 宿主模型 | 首版仅参与阶段摘要与实施建议生成，不接管最终状态与产物路径 |
| Harness 职责 | 固定阶段顺序、结果协议、验证阻断逻辑与 PR 摘要落点 |

## 阶段语义

- `requirements`：提炼 product spec 中的目标、规则、验收基线。
- `docs`：同步 README、ARCHITECTURE、product spec 与 active exec plan；当前 runtime 尚未执行该阶段，属于实现预留。
- `plan`：提炼 active exec plan 中的范围、ULW 与验证步骤。
- `implement`：基于前两阶段输出实施摘要。
- `verify`：读取 `.claude/tmp/last-verify.status` 与 `.claude/tmp/verification-summary.md`。
- `pr-summary`：仅在验证通过时生成摘要文件。
