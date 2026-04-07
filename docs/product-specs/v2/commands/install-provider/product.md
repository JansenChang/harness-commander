# V2 `install-provider` 产品草案

## 当前状态

- draft

## V1 现状

- 已支持多 provider 安装、结果落盘、用户级 / 项目级目标、`auto` / `all`
- 已补齐权限失败结果和 acceptance 自举隔离

## V1 缺陷

- `install-provider` 更像一次性安装动作，而不是 provider 生命周期入口。
- 缺少 doctor / repair / uninstall / auth-check / compatibility 能力。
- 对“用户为什么安装失败、下一步该做什么”的引导还不够强。
- 多宿主环境下，安装结果虽然有记录，但缺少长期维护和状态巡检视角。

## V2 要解决的问题

- 把 `install-provider` 从安装命令扩展成 provider 管理入口。
- 增加健康检查、认证状态检查、修复建议和卸载 / 重装语义。
- 明确项目默认 provider、团队默认 provider、临时 override 三者关系。
- 让 provider 管理成为可持续维护的能力，而不是一次性 setup。

## V2 继承的边界

- `.harness/provider-config.json` 继续是项目级事实源。
- Harness 继续控制目录解析、结果语义和安装结果合同。

## V2 可能推翻的边界

- 仅靠 `install-provider` 一个命令承载全部 provider 生命周期，可能不够清晰。
- `auto` / `all` 的产品语义也许需要和“安装”解耦，转成“发现 / 管理 / 修复”视角。

## 当前开放问题

- V2 是否拆分 `install-provider` 和 `doctor-provider` / `repair-provider`？
- 是否要记录 provider 认证状态、版本兼容性和最近健康检查结果？
- provider 管理应该偏项目级，还是偏用户工作站级？
