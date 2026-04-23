# ADR 0001: 平台层采用双模式兼容改造

## 状态

已采纳

## 背景

CowAgent 原始形态是单实例、单配置、单工作区的通用 Agent 框架。  
本次平台化改造需要支持多租户、显性多 Agent、独立工作区、独立记忆空间和多渠道绑定，但又不能一次性重写内核，否则会失去后续吸收上游更新的能力。

当前仓库里最难绕开的点主要有：

- `config.py` 的全局 `conf()`
- `Bridge` / `AgentBridge` / `ConversationStore` 的单例和缓存
- `channel/web` 直接依赖根工作区
- legacy `app.py` 仍然是现有项目的主要运行入口

## 决策

平台化改造采用“平台层新增 + 内核兼容桥接”的双模式方案：

- 保留 legacy 模式：
  现有 `app.py`、根 `config.json`、单工作区模式继续可运行。
- 新增 platform 模式：
  所有租户、Agent、binding、quota、usage、job 等资源统一进入 `cow_platform/`。
- 对现有内核只做最小必要 patch：
  平台请求进入时，把 `tenant_id / agent_id / binding_id / session_id` 注入运行时作用域；
  现有 Agent 内核继续按原有协议执行。
- 新能力默认优先放在平台层，而不是继续扩展 legacy 全局配置。

## 结果

这样做的收益是：

- 平台功能能逐步落地，不必一次性重写全仓库
- legacy 用户不被破坏，已有启动方式和 web 控制台可继续使用
- 上游升级时，可以把注意力集中在少数 patch 点，而不是整仓冲突

代价是：

- 一段时间内会同时存在 legacy 和 platform 两套路径
- 必须维护 patch register，明确哪些文件是“上游原文件上的兼容修改”

## 后续约束

- 任何新增平台能力，优先落在 `cow_platform/`
- 修改 `bridge/`、`agent/`、`channel/web/` 中的上游文件时，必须登记到 `docs/patch-register.md`
- 吸收上游更新前，先跑全量测试，再逐项核对 patch register
