# Harness-Commander 打包与 Skill 集成

## 1. 业务目标 (The "Why")
- 解决 Harness-Commander 作为独立工具无法无缝集成到 Claude Code 工作流的问题
- 解决开发者需要在多个项目中重复配置 Harness-Commander 的问题
- 解决 AI 开发流程中缺少标准化验收机制的问题
- 提供统一的 Skill 接口，让 Claude Code 可以直接调用 Harness-Commander 的核心能力
- 建立自动化的验收测试框架，确保打包后的工具功能完整且可靠

## 2. 核心逻辑 (Business Logic)
- [关键规则 1]: Harness-Commander 必须支持通过标准 Python 打包工具（setuptools、pip）进行安装
- [关键规则 2]: 打包后的工具必须保留现阶段已对齐的核心 CLI 命令能力，第一轮至少覆盖 `init` 与 `distill`
- [关键规则 3]: 必须提供 provider 安装入口 `harness install-provider`，允许在 Python CLI 内完成跨平台探测、按宿主目录自动安装、配置与结果落盘；Claude Code 项目级 skill 仅保留为兼容包装层，默认安装目标不再局限于仓库内 `.claude/skills/`；其中 Claude user scope 默认目录必须明确为 Linux/macOS 走 `~/.claude/skills/harness-commander`、Windows 走 `%APPDATA%/Claude/skills/harness-commander`；同时产品层必须明确支持 Cursor、Claude、Codex、OpenClaw、Trae、Copilot 等宿主工具 provider
- [关键规则 4]: 包装层不再假设所有宿主都消费同一种 `SKILL.md`；Claude/Codex/OpenClaw/Trae/Copilot 当前走 `skill` wrapper，Cursor 当前走 `command` wrapper
- [关键规则 5]: 宿主集成必须支持 CLI 参数的原样透传，保持 `init` 与 `distill` 的命令语义一致性
- [关键规则 6]: 必须建立最小化验收测试套件，验证打包后工具与多宿主 wrapper 包装层的核心功能
- [关键规则 7]: 第一轮验收测试必须优先覆盖 `init` 与 `distill` 两个关键业务场景
- [关键规则 8]: 打包配置必须包含所有运行时依赖，确保工具在干净环境中正常运行
- [关键规则 9]: Claude/Codex/OpenClaw/Trae/Copilot skill 定义必须遵循各自 skill 目录规范，Cursor command 定义必须遵循 command 目录约定，并提供清晰的命令描述和参数提示
- [关键规则 10]: 必须提供最小 install/uninstall 脚本，支持在本仓库内安装或移除 Claude 项目级兼容 skill
- [关键规则 11]: `distill` 默认必须被明确标注为规则/启发式提炼能力；只有显式传入 `--mode host-model` 或 `--mode auto` 时，才允许通过所选 provider 对应的本地 CLI 调用宿主模型
- [关键规则 12]: 宿主集成必须支持 dry-run 模式，允许用户在应用变更前预览效果
- [关键规则 13]: 必须提供安装后的 smoke 验证机制，确保工具正确集成到 Claude Code 环境及其他受支持宿主的 wrapper 目录
- [关键规则 14]: `harness install-provider` 必须支持 `--scope user|project` 与 `--install-mode copy|link`，并把本次解析到的 wrapper 类型、目标目录、安装模式和失败原因写入 `.harness/provider-config.json`
- [关键规则 15]: 所有运行时引用的 provider 模板必须统一放在 `src/harness_commander/host_templates/` 下，并作为 package data 随 Python 包分发；不得依赖 repo root 模板路径作为事实源

## 3. 验收标准 (Acceptance Criteria - AC)
- AC 1: 通过 `pip install .` 或 `pip install -e .` 安装后，必须能在系统 PATH 中直接使用 `harness` 命令
- AC 2: 安装后执行 `harness --help` 必须显示完整的命令帮助信息，至少包含 `init` 与 `distill`
- AC 3: 必须支持按 provider 把 `skill` 或 `command` wrapper 安装到用户侧宿主目录，不能默认只依赖项目级 `.claude/skills/harness/SKILL.md`
- AC 4: Claude/Cursor/Codex/OpenClaw/Trae/Copilot 等宿主的集成定义必须支持 `init` 与 `distill` 的参数透传，包括 `-p`、`--json`、`--dry-run`、`--verbose`
- AC 5: `harness install-provider` 必须支持 `--scope user|project` 与 `--install-mode copy|link`
- AC 6: 必须提供安装脚本 `install-skill.sh`，作为 Claude 项目级兼容安装入口，而不是唯一安装入口
- AC 7: 必须提供卸载能力，能够移除已安装的宿主级或项目级 wrapper 产物
- AC 8: 安装 Claude skill 后，在 Claude Code 中输入 `/harness init -p /tmp/test-project` 必须可以进入执行流程
- AC 9: 安装 Claude skill 后，在 Claude Code 中输入 `/harness distill -p /tmp/test-project /tmp/test-project/requirements.md --json` 必须可以进入执行流程
- AC 10: 必须创建自动化验收测试目录 `tests/acceptance/`，并至少覆盖 4 个最小场景
- AC 11: 验收测试必须覆盖：`harness --help`、wrapper 源文件存在、`install-provider` 主路径、`init` smoke、`distill` smoke
- AC 12: 每个验收测试必须包含明确断言，验证命令执行结果符合预期
- AC 13: 验收测试执行命令 `pytest tests/acceptance/` 必须全部通过
- AC 14: 验收测试必须包含测试数据清理机制，确保测试不会污染系统环境
- AC 15: 文档必须明确说明 `distill` 当前是 heuristic 模式，不应表述为已接入大模型总结
- AC 16: 宿主集成必须支持相对路径和绝对路径的解析，与 CLI 行为保持一致
- AC 17: 打包配置必须包含最小化的运行时依赖，避免引入不必要的包依赖
- AC 18: `auto` 与 `all` 必须返回完整多 provider 结果表，并包含目标目录解析、wrapper 类型、安装模式和失败原因字段

## 4. 异常处理 (Edge Cases)
- 当目标系统已存在旧版本 Harness-Commander 时，安装过程必须正确处理版本升级
- 当 Claude Code 配置目录不存在或无写入权限时，Skill 安装必须提供明确错误提示
- 当打包过程中代码质量检查失败时，必须停止打包并输出具体的失败原因
- 当验收测试因环境问题失败时，必须提供详细的调试信息，帮助定位问题
- 当 Skill 参数映射错误导致命令执行失败时，必须回退到原始错误信息，而不是静默失败
- 当用户尝试在非项目目录中使用 Harness-Commander 时，必须提供友好的引导信息
- 当打包配置文件（pyproject.toml）损坏或缺失时，必须使用内置默认配置继续打包
- 当 Skill 安装过程中遇到配置冲突时，必须提示用户选择覆盖或跳过
- 当验收测试数据清理失败时，必须记录警告但允许测试继续执行
- 当版本号格式不符合语义化版本规范时，打包过程必须拒绝继续执行
- 当运行时依赖包版本冲突时，必须优先保证 Harness-Commander 核心功能的可用性
- 当 Claude Code 更新导致 Skill 接口变化时，必须提供迁移指南或兼容层
- 当用户系统缺少 Python 运行时或版本不兼容时，安装脚本必须明确提示要求
- 当打包过程中遇到文件权限问题时，必须区分可修复问题和阻断性问题
- 当验收测试在 CI/CD 环境中执行时，必须适配不同的环境变量和工作目录设置