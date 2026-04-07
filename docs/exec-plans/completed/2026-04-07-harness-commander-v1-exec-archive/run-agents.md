# `run-agents` 执行计划

## Goal

让 `harness run-agents` 在 V1 中稳定串起 product spec、active exec plan、验证结果和 PR summary，而不是让宿主工具自由跳阶段。

## Scope

- product spec / plan 读取
- 阶段顺序与阶段摘要
- provider 默认解析与临时 override
- verify 阻断与 PR summary 落盘

## 当前硬化进展（2026-04-07）

- 已补齐 `verify` 状态文件缺失、状态非 `PASS`、计划校验失败时的阻断覆盖。
- 已补齐 `--dry-run` 下 PR summary 只返回将创建产物、不真实落盘的覆盖。
- 已补齐 verification summary 缺失时的 PR 摘要 fallback 文案覆盖。
- 已补齐 PR summary 目标路径冲突时自动避让新文件名的覆盖。

## ULW

- `RA-ULW-1`：固定 requirements -> plan -> implement -> verify -> pr-summary 阶段顺序
- `RA-ULW-2`：统一 provider 默认读取与 `--provider` override 语义
- `RA-ULW-3`：在 verify 未通过时阻断 PR summary 生成
- `RA-ULW-4`：补齐阶段摘要、JSON 结果和产物目录的一致性

## 宿主模型参与

- 当前仅允许参与阶段摘要和实施建议生成。
- 最终状态、阶段顺序、验证阻断和产物落点必须由 Harness 控制。

## References

- `docs/product-specs/v1/commands/run-agents/product.md`
- `docs/product-specs/v1/commands/run-agents/protocol.md`
- `docs/product-specs/v1/commands/run-agents/acceptance.md`
