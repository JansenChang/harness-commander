# `harness install-provider` 产品定义

## 解决的问题

- 过去 provider 主要靠运行时 `--provider` 逐次传入，缺少项目级默认绑定。
- 现有安装样板偏向 `install-skill.sh`，不适合作为跨平台 provider 主入口。
- 多 provider 场景缺少统一安装结果表与默认 provider 事实源。

## 具体作用

- 提供跨平台 Python 安装入口，用于按 provider wrapper 类型执行真实安装或配置落盘。
- 把 provider 安装结果写入 `.harness/provider-config.json`，并在支持时安装用户级或项目级 wrapper。
- 支持单 provider、`auto` 自动探测、`all` 全量尝试三种安装目标。

## 当前实现目标

- 支持目标：`cursor`、`claude`、`codex`、`openclaw`、`trae`、`copilot`、`auto`、`all`。
- `install-provider` 的主职责不是只安装到仓库内 `.claude/skills/`，而是按 provider 类型与用户本机环境，把 `skill` / `command` 等 wrapper 自动安装到对应宿主的用户级或项目级目录。
- `auto` 必须基于本机探测结果只处理已安装且可识别目录的宿主；`all` 必须遍历全部受支持 provider，并对每个 provider 独立执行目录解析、安装尝试与结果落盘。
- 当某个 provider 已知支持用户级 skill 目录时，主路径应优先安装到该用户目录；仅在 provider 明确只支持项目级目录时，才允许落到项目目录。
- Claude 的 `install-skill.sh` 保留为兼容入口，但主安装语义由 Python CLI 定义，且不再把 `.claude/skills/harness/SKILL.md` 视为唯一目标。

## 安装语义

- `claude`：当前安装 `skill` wrapper，Linux/macOS 默认落到 `~/.claude/skills/harness-commander`，Windows 默认落到 `%APPDATA%/Claude/skills/harness-commander`；项目级安装仅作为兼容或显式选择。
- `cursor`：当前安装 `command` wrapper，默认落到 Cursor command 目录。
- `trae`：当前安装 `skill` wrapper，默认落到 Trae skill 目录。
- `codex`、`openclaw`、`copilot`：当前安装 `skill` wrapper，默认落到各自 skill 目录。
- `auto`：自动挑选当前机器上可识别且可写入的宿主目录，不应强行只安装 Claude。
- `all`：面向“全适配”场景，要求对全部已支持宿主执行安装或配置尝试，并返回逐项状态。

## 结果要求

- 每个 provider 的安装结果必须包含：探测到的宿主、解析出的目标目录、wrapper 类型、安装模式、真实写入产物或未写入原因。
- 如果宿主未安装、目录不存在、权限不足或当前 provider 仍未实现真实安装，必须在结果里明确标记，而不是静默回退到 Claude 或仓库内 `.claude/skills/`。

## 产物

- `.harness/provider-config.json`
- 支持时写入各宿主 wrapper 落点，例如 `.claude/skills/harness/SKILL.md`、`.cursor/commands/harness.md`
- `CommandResult.meta.results`
