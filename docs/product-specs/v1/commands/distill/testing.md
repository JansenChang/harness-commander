# `harness distill` 测试标准

- 必测：`--mode heuristic`、`--mode host-model`、`--mode auto` fallback、`--provider`、源文件不存在、四类核心信息输出、`--dry-run`、`--json`
- 通过标准：首先保证不误导 AI，其次保证输出格式稳定；宿主模型参与后结果协议和产物路径不漂移
