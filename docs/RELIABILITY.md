# RELIABILITY

## 这个文件是做什么的

用于规定系统在错误处理、日志记录、重试、超时和降级方面的硬性要求。

## 适合写什么

- 接口异常处理规范
- 重试策略和超时策略
- 日志字段要求和禁止项
- 告警、监控、降级和兜底方案

## 推荐用法

- AI 在写接口、任务调度、集成第三方时先参考这里
- 防止出现只实现 happy path、不处理失败路径的代码
- 把稳定性要求前置到开发阶段，而不是线上出问题后补救

## 环境稳定性约束

- 运行测试、验收、CLI smoke 和本地验证时，默认必须优先使用项目虚拟环境中的 `.venv/bin/...` 命令。
- 不允许默认依赖系统 PATH 中的 `python`、`pytest`、`harness` 是否存在；这类依赖会导致不同机器上出现假失败。
- 如果测试代码、脚本或验收流程需要调用 CLI，必须显式注入 `.venv/bin` 到 PATH，或直接调用 `.venv/bin/python`、`.venv/bin/pytest`、`.venv/bin/harness`。
- 当出现 `command not found`、`No module named pytest`、`harness command not found in PATH` 一类错误时，先检查是否误用了系统环境，而不是直接判断实现有问题。
- 文档、脚本和示例命令在可控情况下应优先展示 `.venv/bin/...` 形式，降低环境漂移带来的排查成本。
