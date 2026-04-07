# `harness install-provider` 协议

| 项目 | 定义 |
| --- | --- |
| 命令 | `harness install-provider --provider <target>` |
| 参数 | `-p, --root`；`--provider <target>`；`--scope <user\|project>`；`--install-mode <copy\|link>`；`--dry-run`；`--json` |
| 必填参数 | `--provider` |
| target | `cursor`、`claude`、`codex`、`openclaw`、`trae`、`copilot`、`auto`、`all` |
| scope | `user` 为默认值；`project` 仅在显式指定时写入项目目录 |
| install-mode | `copy` 为默认值；`link` 表示用符号链接安装 wrapper |
| 配置落点 | `.harness/provider-config.json` |
| 安装目标落点 | 按 provider 与 OS 解析出的用户级或项目级 wrapper 目录；Claude/Codex/OpenClaw/Trae/Copilot 当前写入 `skill` wrapper，Cursor 当前写入 `command` wrapper |
| JSON `meta` | `root`、`provider`、`scope`、`install_mode`、`install_targets`、`results`、`default_provider`、`installed_providers`、`dry_run` |

## 目标语义

- 单 provider：仅处理对应 provider。
- `auto`：遍历全部受支持 provider，基于本机探测结果只对已识别且能解析目录的宿主执行安装；未探测到或无法解析目标目录的 provider 也必须写入明确结果，而不是静默忽略。
- `all`：对全部支持 provider 执行安装尝试，输出完整结果表；每个 provider 独立完成探测、目录解析、安装尝试与失败原因记录。

## wrapper 语义

- `claude`：`skill` wrapper，默认 user scope 目标为 Claude 用户 skill 目录。
- `cursor`：`command` wrapper，默认 user scope 目标为 Cursor 用户 command 目录。
- `trae`：`skill` wrapper，默认 user scope 目标为 Trae 用户 skill 目录。
- `codex`、`openclaw`、`copilot`：`skill` wrapper，默认 user scope 目标为各自用户 skill 目录。
- 未显式要求 `--scope project` 时，不允许默认回退到仓库内 `.claude/skills/` 或其他项目目录。

## 配置语义

- 项目级 provider 配置事实源固定为 `.harness/provider-config.json`。
- 最小字段包括：`version`、`default_provider`、`installed_providers`、`installation_results`、`last_resolved_provider`。
- `installed_providers` 只应包含真实安装成功的 provider；不能仅因写入配置就被视为 installed。
- `installation_results[provider]` 至少记录：`status`、`support_level`、`wrapper_kind`、`installation_mode`、`install_attempted`、`artifact_paths`、`resolved_target_dir`、`resolved_target_file`、`target_scope`、`host_detected`、`failure_reason_code`、`failure_reason_detail`、`dry_run`、`installer`。
- `default_provider` 供 `distill` 的 `host-model` / `auto` 模式和 `run-agents` 默认读取。

## support level

- `fully_supported`
- `config_only`
- `manual_setup_required`
