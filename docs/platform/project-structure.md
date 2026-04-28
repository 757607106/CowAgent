# Platform Project Structure

本文档记录当前平台二开层的工程目录边界，避免后续整理时把上游内核、平台层、运行时产物混在一起。

## 顶层边界

- `agent/`、`bridge/`、`channel/`、`common/`、`models/`、`plugins/`、`skills/`、`translate/`、`voice/`：CowAgent 上游内核和 legacy 扩展目录，升级时优先按 `docs/patch-register.md` 做差异复核。
- `cow_platform/`：平台内核层，包含 API、领域模型、仓储、服务、运行时隔离、worker 和部署检查。
- `channel/web/`：Web channel 后端入口和前端工程，后端路由仍在该目录，前端源码已收敛到 `channel/web/frontend/`。
- `channel/web/handlers/`：Web 控制台 route handler 模块；`web_channel.py` 保留 WebChannel 主类、运行时作用域 helper 和旧类名 re-export。
- `docker/`：容器和 Compose 部署文件。
- `scripts/`：通用启动脚本和兼容入口；平台真实场景脚本放在 `scripts/platform/`。
- `tests/`：测试目录，按 `unit/`、`integration/`、`e2e/` 和 `support/` 分层。
- `docs/`：上游文档、平台治理文档和平台设计文档。

## Web 前端

- `channel/web/frontend/modern/`：React + TypeScript + Vite 前端工程。
- `channel/web/frontend/modern/src/pages/`：控制台页面。
- `channel/web/frontend/modern/src/chat/`：聊天流式消息、Markdown 和 provider 适配。
- `channel/web/frontend/modern/src/services/`：浏览器端 API 和 HTTP scope 工具。
- `channel/web/frontend/modern/dist/`：构建产物，运行时 `/chat` 和 `/assets/*` 只读取这里。
- 旧版静态前端已删除，Web 控制台只保留 modern 前端工程和构建产物。

## Web 后端

- `channel/web/web_channel.py`：WebChannel 主类、认证/租户作用域、Agent 工作区解析、会话 store 适配和 handler 兼容导出。
- `channel/web/handlers/core.py`：根路由、认证检查、登录/注册、消息、上传、静态资源等基础 handler。
- `channel/web/handlers/configuration.py`：平台初始化与废弃 `/config` 路由。
- `channel/web/handlers/channel_admin.py`：legacy 全局渠道与微信扫码登录入口。
- `channel/web/handlers/platform.py`：平台/租户模型、租户、成员、Agent、绑定、渠道配置、用量等平台化 API。
- `channel/web/handlers/callbacks.py`：租户渠道回调入口。
- `channel/web/handlers/workspace.py`：技能、记忆、知识库、任务、会话、日志和 MCP 工作区 API。
- `channel/web/handlers/dependencies.py`：handler 到 `web_channel.py` 运行时 helper 的延迟代理，避免循环导入并保留测试 monkeypatch 能力。

## 测试

- `tests/unit/`：不依赖真实 PostgreSQL 或外部服务的单元测试。
- `tests/integration/`：跨模块集成测试；需要 PostgreSQL 的用例由 `tests/conftest.py` 做环境门禁。
- `tests/e2e/`：真实进程、HTTP 或部署契约测试。
- `tests/support/`：测试桩和共享 fake repository。

## 运行时产物

- `config.json`、`cow/workspaces/`、`tmp/`、`*.log`、`node_modules/`、`dist/`、`test-results/` 不进入版本库。
- 租户工作区文件属于运行时数据。如果要沉淀通用模板，应放到明确的模板目录，不应提交在 `cow/workspaces/tenant-*` 下。
