# `harness install-provider` 验收标准

- 成功路径：`harness install-provider --provider claude` 必须创建 `.harness/provider-config.json`，并把 Claude `skill` wrapper 安装到解析出的用户级 Claude skill 目录；其中 Linux/macOS 默认路径为 `~/.claude/skills/harness-commander`，Windows 默认路径为 `%APPDATA%/Claude/skills/harness-commander`；返回统一 JSON 结果。
- 单 provider 路径：`harness install-provider --provider cursor|codex|openclaw|trae|copilot` 必须先解析对应宿主目录与 wrapper 类型，并在支持时写入真实产物；未支持时也必须返回明确原因、目标路径与 wrapper 信息。
- scope 路径：显式 `--scope project` 时，Claude/Codex/OpenClaw/Trae/Copilot 应写入各自项目级 skill 目录，Cursor 应写入项目级 command 目录；未显式指定时默认走 `user`。
- install-mode 路径：`--install-mode copy` 写入真实文件，`--install-mode link` 写入符号链接；结果字段必须反映本次安装模式。
- 自动探测路径：`harness install-provider --provider auto` 必须至少生成完整安装结果表；当探测到多个可安装宿主时应分别安装到各自用户目录，而不是只落到 Claude 或项目目录。
- 全量尝试路径：`harness install-provider --provider all` 必须覆盖全部受支持 provider 并写入结果；每个 provider 都需要产出探测、目录解析、安装尝试和失败原因状态。
- `--dry-run`：返回将写入的 wrapper/config 产物描述，但不实际落盘。
- 结果协议：`meta.results`、`meta.default_provider`、`meta.installed_providers` 必须稳定可解析，且每项结果都包含 `resolved_target_dir`、`resolved_target_file`、`target_scope`、`host_detected`、`wrapper_kind`、`failure_reason_code` 等目标目录解析与执行信息。
- 回退约束：未显式要求项目级安装时，不允许静默回退到仓库内 `.claude/skills/` 作为默认落点，也不允许把未识别 provider 伪装成 Claude 成功安装。
- Windows 兼容性：主安装入口必须是 Python CLI，不应依赖 shell 脚本作为唯一主路径。
