# Harness-Commander 打包与 Skill 集成

## 1. 业务目标 (The "Why")
- 解决 Harness-Commander 作为独立工具无法无缝集成到 Claude Code 工作流的问题
- 解决开发者需要在多个项目中重复配置 Harness-Commander 的问题
- 解决 AI 开发流程中缺少标准化验收机制的问题
- 提供统一的 Skill 接口，让 Claude Code 可以直接调用 Harness-Commander 的核心能力
- 建立自动化的验收测试框架，确保打包后的工具功能完整且可靠

## 2. 核心逻辑 (Business Logic)
- [关键规则 1]: Harness-Commander 必须支持通过标准 Python 打包工具（setuptools、pip）进行安装
- [关键规则 2]: 打包后的工具必须保留所有 CLI 命令的完整功能，包括 `init`、`propose-plan`、`plan-check`、`sync`、`distill`、`check`、`collect-evidence`
- [关键规则 3]: 必须提供 Claude Code Skill 集成方案，允许通过 `/harness` 命令调用 Harness-Commander
- [关键规则 4]: Skill 集成必须支持所有 CLI 参数的原样传递，保持命令语义一致性
- [关键规则 5]: 必须建立自动化验收测试套件，验证打包后工具的核心功能
- [关键规则 6]: 验收测试必须覆盖关键业务场景，包括初始化、计划生成、合规检查和证据收集
- [关键规则 7]: 打包配置必须包含所有运行时依赖，确保工具在干净环境中正常运行
- [关键规则 8]: Skill 定义必须遵循 Claude Code Skill 开发规范，提供清晰的命令描述和参数映射
- [关键规则 9]: 必须提供开发环境与生产环境的双重打包方案，支持快速迭代和稳定发布
- [关键规则 10]: 打包过程必须自动执行代码质量检查（类型检查、格式化、linting）
- [关键规则 11]: 必须生成版本化的发布包，支持回滚和版本追踪
- [关键规则 12]: Skill 集成必须支持 dry-run 模式，允许用户在应用变更前预览效果
- [关键规则 13]: 必须提供安装后的配置验证机制，确保工具正确集成到 Claude Code 环境

## 3. 验收标准 (Acceptance Criteria - AC)
- AC 1: 通过 `pip install .` 安装后，必须能在系统 PATH 中直接使用 `harness` 命令
- AC 2: 安装后执行 `harness --help` 必须显示完整的命令帮助信息，包含所有子命令
- AC 3: 打包过程必须自动执行 `mypy`、`ruff`、`black`、`isort` 检查，任一检查失败则打包失败
- AC 4: 必须提供 `make build` 或等价的构建命令，一键完成打包流程
- AC 5: 必须创建 Claude Code Skill 定义文件 `harness-skill.json`，定义 `/harness` 命令及其参数映射
- AC 6: Skill 定义必须支持所有 CLI 参数的映射，包括 `--json`、`--dry-run`、`--verbose` 等选项
- AC 7: 必须提供安装脚本 `install-skill.sh`，将 Skill 集成到 Claude Code 配置中
- AC 8: 安装 Skill 后，在 Claude Code 中输入 `/harness init -p /tmp/test-project` 必须正确执行初始化
- AC 9: 必须创建自动化验收测试目录 `tests/acceptance/`，包含至少 5 个核心场景测试
- AC 10: 验收测试必须覆盖：项目初始化、执行计划生成、计划合规检查、文档同步、证据收集
- AC 11: 每个验收测试必须包含明确的断言，验证命令执行结果符合预期
- AC 12: 验收测试执行命令 `pytest tests/acceptance/` 必须全部通过
- AC 13: 必须提供测试数据清理机制，确保测试不会污染系统环境
- AC 14: 打包过程必须生成版本号，格式为 `harness-commander-{version}.tar.gz`
- AC 15: 必须提供版本兼容性检查，确保新版本不会破坏现有项目的使用
- AC 16: 必须创建 `CHANGELOG.md` 文件，记录每个版本的变更内容
- AC 17: Skill 集成必须支持相对路径和绝对路径的解析，与 CLI 行为保持一致
- AC 18: 必须提供卸载脚本 `uninstall-skill.sh`，完整移除 Skill 集成
- AC 19: 验收测试必须在干净虚拟环境中执行，验证工具不依赖开发环境特定配置
- AC 20: 打包配置必须包含最小化的运行时依赖，避免引入不必要的包依赖

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