# Web Channel

提供 AI Agent 数字员工中台的 Web 控制台入口，前端采用 React + Ant Design + Ant Design X。

# 使用说明

 - 在 `config.json` 配置文件中的 `channel_type` 字段填入 `web`
 - 程序运行后将监听9899端口，浏览器访问 http://localhost:9899/chat 即可使用
 - 监听端口可以在配置文件 `web_port` 中自定义
 - 对于Docker运行方式，如果需要外部访问，需要在 `docker-compose.yml` 中通过 ports配置将端口监听映射到宿主机

# 前端结构

 - `ui/src/` 是前端源码（React + TypeScript + Vite）
 - `ui/dist/` 是前端构建产物，`/chat` 固定返回 `ui/dist/index.html`
 - `/assets/*` 路由仅从 `ui/dist/` 解析静态资源
 - Web 基础 handler（`auth/chat/assets/version/upload`）已收敛到 `channel/web/handlers/core.py`，`web_channel.py` 仅保留组装与业务 handler
 - Web 路由总表已收敛到 `channel/web/route_table.py`，避免在 `web_channel.py` 中维护超长路由元组

# 前端构建

进入 `channel/web/ui` 后执行：

 - `npm install`
 - `npm run typecheck`
 - `npm run build`

> 说明：`web_frontend_mode` 已废弃，运行时始终使用 modern 前端。
