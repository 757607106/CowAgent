# Web Channel

提供了一个默认的AI对话页面，可展示文本、图片等消息交互，支持markdown语法渲染，兼容插件执行。

# 使用说明

 - 在 `config.json` 配置文件中的 `channel_type` 字段填入 `web`
 - 程序运行后将监听9899端口，浏览器访问 http://localhost:9899/chat 即可使用
 - 监听端口可以在配置文件 `web_port` 中自定义
 - 对于Docker运行方式，如果需要外部访问，需要在 `docker-compose.yml` 中通过 ports配置将端口监听映射到宿主机

# 前端结构

 - `chat.html + static/` 是默认的 `legacy` 控制台前端
 - `ui/dist/` 是可选的 `modern` 前端构建产物（按需启用）
 - `/assets/*` 路由会根据前端模式自动在 `legacy` 与 `modern` 目录中解析资源，避免重复路由逻辑
 - Web 基础 handler（`auth/chat/assets/version/upload`）已收敛到 `channel/web/handlers/core.py`，`web_channel.py` 仅保留组装与业务 handler
 - Web 路由总表已收敛到 `channel/web/route_table.py`，避免在 `web_channel.py` 中维护超长路由元组

# 前端模式配置

可通过配置项 `web_frontend_mode` 控制：

 - `legacy`（默认）：始终使用 `chat.html + static/`
 - `modern`：优先使用 `ui/dist/index.html`，若构建产物缺失自动回退到 `legacy`
 - `auto`：存在 `ui/dist/index.html` 时自动走 `modern`，否则走 `legacy`
