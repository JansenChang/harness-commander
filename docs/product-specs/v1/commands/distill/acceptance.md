# `harness distill` 验收标准

- 成功路径：生成 `docs/references/*-llms.txt`，输出四类核心信息并返回统一 JSON 结果
- 失败路径：源文件不存在、无法读取、启发式与宿主模型路径都无法可靠提炼重点、目标文件无法写入时失败
- `--dry-run`：返回目标产物描述但不实际写入
- 模式与 fallback：默认模式必须是 `heuristic`；`auto` 在宿主模型不可用、超时、返回空结果或非法结构时必须回退，并在 `warnings` 与 `meta` 中保留回退信息
- provider：`--provider` 必须接受 `cursor`、`claude`、`codex`、`openclaw`、`trae`、`copilot`，并把 provider 元信息写入 `meta`
- 宿主模型边界：输出模板、文件命名、目标路径和失败条件必须由 Harness 控制
