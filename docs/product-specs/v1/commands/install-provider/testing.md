# `harness install-provider` 测试标准

- 必测参数组合：`--provider claude`、`--provider cursor`、`--provider codex`、`--provider openclaw`、`--provider trae`、`--provider copilot`、`--provider auto`、`--provider all`、`--scope user`、`--scope project`、`--install-mode copy`、`--install-mode link`、`--json`、`--dry-run`。
- 必测 OS 路径解析：macOS、Linux、Windows 三类路径规则都能按 provider 返回稳定的 user scope 目录；不得把某个开发机的绝对路径写死到结果或测试中。
- 必测 wrapper 类型：Claude/Codex/OpenClaw/Trae/Copilot 返回 `skill` wrapper 目标，Cursor 返回 `command` wrapper 目标。
- 必测：`--provider claude` 会写入 `.harness/provider-config.json`，并优先写入用户 Claude skill 目录；Linux/macOS 默认应解析到 `~/.claude/skills/harness-commander`，Windows 默认应解析到 `%APPDATA%/Claude/skills/harness-commander`，而不是默认只写仓库内 `.claude/skills/harness/SKILL.md`。
- 必测：`--provider cursor --scope project` 会解析到 `.cursor/commands`；`--provider trae --scope project` 会解析到 `.trae/skills/harness`。
- 必测：`--install-mode link` 在支持路径上创建符号链接；`--install-mode copy` 创建真实文件副本。
- 必测：`--provider auto` 在存在多个宿主时，会按探测结果分别安装到对应用户目录，而不是只返回 Claude 结果。
- 必测：`--provider all` 会覆盖全部受支持 provider，并返回逐项目录解析、安装尝试与状态结果。
- 必测：`--dry-run` 返回 `would_create` / `would_overwrite` 类产物，但不真实写入 wrapper 或 `.harness/provider-config.json`。
- 必测：`meta.results` 返回完整 provider 安装结果表，并包含 `resolved_target_dir`、`resolved_target_file`、`target_scope`、`host_detected`、`artifact_paths`、`failure_reason_code`、`failure_reason_detail`、`install_attempted`、`installation_mode`、`wrapper_kind` 等字段。
- 必测：默认 provider、已安装 provider 列表与结果表结构稳定；只有真实安装成功的 provider 会进入 `installed_providers`。
- 通过标准：跨平台 Python 入口可用；运行时默认 provider 可被后续命令消费；多宿主用户环境下安装行为与探测结果一致；`auto` / `all` 对六个 provider 都返回稳定结果合同。
