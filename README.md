# Harness-Commander

统一 Harness 生命周期治理命令入口，为 Claude、Codex、Trae 等开发者工具提供标准化的治理能力。

## 🎯 核心价值

- **统一入口**: 一个命令入口管理 Harness 全生命周期，覆盖初始化、规划、校验、同步、审计、脱水和取证七类能力
- **AI 友好**: 所有命令同时支持人类可读摘要和机器可解析的 JSON 输出，便于 AI 工具集成
- **文档驱动**: 严格执行 `docs/` 目录下的规范文档，确保代码与文档保持同步
- **证据留痕**: 自动记录每轮任务的执行证据，形成可回溯的验证记录

## 📦 快速开始

### 安装

```bash
# 从源码安装
git clone <repository-url>
cd harness-commander
pip install -e .

# 验证安装
harness --help
```

### 基本使用

```bash
# 初始化项目结构
harness init -p /path/to/your/project

# 生成执行计划
harness propose-plan -p /path/to/project --input "添加用户认证功能"

# 校验计划合规性
harness plan-check -p /path/to/project docs/exec-plans/active/2026-04-06-user-auth.md

# 同步重大变更到文档
harness sync -p /path/to/project

# 压缩长文档为 AI 参考材料
harness distill -p /path/to/project docs/long-specification.md

# 执行项目审计
harness check -p /path/to/project

# 收集执行证据
harness collect-evidence -p /path/to/project \
  --command "make test" \
  --exit-code 0 \
  --summary "所有测试通过" \
  --status success \
  --log "测试运行 2.3 秒" \
  --log "通过率 100%"
```

## 🔧 Claude Code Skill 集成

Harness-Commander 可以作为 Skill 集成到 Claude Code，提供更便捷的使用体验。

### Skill 安装

```bash
# 1. 确保 Harness-Commander 已安装
pip install -e .

# 2. 安装 Skill 集成
./install-skill.sh
```

### Skill 使用

在 Claude Code 对话中直接使用 `/harness` 命令：

```
/harness init -p /path/to/project
/harness propose-plan --input "实现支付功能"
/harness check --dry-run
```

### Skill 参数映射

所有 CLI 参数都支持通过 Skill 调用：
- `-p, --root` → 项目根目录
- `--json` → JSON 输出模式
- `--dry-run` → 预览模式
- `--verbose` → 详细日志

## 📁 项目结构

```
harness-commander/
├── src/harness_commander/
│   ├── cli.py              # CLI 入口
│   ├── application/        # 应用层（命令实现）
│   ├── domain/             # 领域层（模型定义）
│   └── infrastructure/     # 基础设施层（文件操作、模板等）
├── docs/                   # 治理文档
│   ├── design-docs/        # 设计文档
│   ├── exec-plans/         # 执行计划
│   ├── product-specs/      # 产品需求
│   ├── generated/          # 生成文档
│   └── references/         # AI 参考材料
├── tests/                  # 测试套件
├── pyproject.toml          # 项目配置
└── README.md               # 本文档
```

## 📚 核心文档

开始使用前，请阅读以下关键文档：

1. **`ARCHITECTURE.md`** - 系统架构与模块边界
2. **`AGENTS.md`** - AI 行为规范与决策边界
3. **`docs/PLANS.md`** - 当前 Roadmap 与执行重点
4. **`docs/design-docs/core-beliefs.md`** - 团队技术原则
5. **`docs/product-specs/harness-commander.md`** - 完整产品规格

## 🧪 开发与测试

### 开发环境设置

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 2. 安装开发依赖
pip install -e ".[dev]"

# 3. 运行代码质量检查
make lint    # 或: ruff check . && black --check . && isort --check .
make type    # 或: mypy src/
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_cli.py

# 运行验收测试
pytest tests/acceptance/
```

### 构建打包

```bash
# 构建分发包
make build

# 清理构建产物
make clean
```

## 🚀 高级功能

### JSON 输出模式

所有命令都支持 `--json` 参数，输出结构化的结果供程序处理：

```bash
harness init -p /tmp/test-project --json
```

输出示例：
```json
{
  "command": "init",
  "status": "success",
  "summary": "初始化完成，创建了 15 个文件，跳过了 2 个已有文件",
  "artifacts": ["AGENTS.md", "ARCHITECTURE.md", "docs/..."],
  "warnings": [],
  "errors": []
}
```

### Dry-run 预览模式

可能修改文件的命令都支持 `--dry-run`，预览将发生的变更而不实际写入：

```bash
harness init -p /tmp/test-project --dry-run
harness sync -p /path/to/project --dry-run
```

### 自定义模板

初始化文件模板由 `src/harness_commander/init_templates/` 中的包内资源提供，`docs/design-docs/init-templates.md` 负责说明模板规范与内容基线。

## 🔄 生命周期管理

Harness-Commander 支持完整的治理生命周期：

1. **初始化** (`init`) - 补齐目录结构与基础模板
2. **规划** (`propose-plan`) - 将需求转化为可执行计划
3. **校验** (`plan-check`) - 确保计划引用正确约束文档
4. **同步** (`sync`) - 将代码重大变更同步到文档
5. **脱水** (`distill`) - 调用大模型能力将长文档压缩为 AI 参考材料
6. **审计** (`check`) - 对照质量、安全和信仰执行审计
7. **取证** (`collect-evidence`) - 留存任务执行证据

## 📋 版本兼容性

- **Python**: >= 3.10
- **操作系统**: Linux, macOS, Windows (WSL 推荐)
- **Claude Code**: >= 1.0.0 (Skill 集成)

## 🐛 问题反馈

遇到问题或需要新功能？

1. 检查 `docs/exec-plans/tech-debt-tracker.md` 是否已记录类似问题
2. 查看现有 Issue 或创建新 Issue
3. 提供复现步骤、错误信息和环境详情

## 📄 许可证

[请根据项目实际情况填写许可证信息]

---

**提示**: 开始任何实现、重构、排查或文档补充前，请 AI 先阅读相关 `docs/` 文件。如果 `docs/` 中已有规范、计划、设计或业务约束，默认严格按这些文件执行。