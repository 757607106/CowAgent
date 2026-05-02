from __future__ import annotations

import os

from bridge.reply import Reply, ReplyType
from common.log import logger


def create_file_reply(file_info: dict, text_response: str = "") -> Reply:
    file_type = file_info.get("file_type", "file")
    file_path = file_info.get("path")
    file_url = f"file://{file_path}"

    if file_type == "image":
        logger.info(f"[AgentBridge] Sending image: {file_url}")
        reply = Reply(ReplyType.IMAGE_URL, file_url)
    else:
        log_type = file_type if file_type in {"document", "video", "audio"} else "generic file"
        logger.info(f"[AgentBridge] Sending {log_type}: {file_url}")
        reply = Reply(ReplyType.FILE, file_url)
        reply.file_name = file_info.get("file_name", os.path.basename(file_path))

    if text_response:
        reply.text_content = text_response
    return reply
