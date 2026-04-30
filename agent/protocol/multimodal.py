"""
Utilities for routing native multimodal image input through the normal chat path.

The existing channels already append uploaded images as text markers such as
``[图片: /path/to/file.png]``.  These helpers keep that contract intact while
allowing vision-capable chat models to receive structured image content directly.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import re
from typing import Any, Callable

from common import const
from common.log import logger


IMAGE_REF_RE = re.compile(r"\[图片:\s*([^\]]+)\]")

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

_OPENAI_VISION_PREFIXES = (
    "gpt-4o",
    "gpt-4.1",
    "gpt-5",
    "o3",
    "o4",
)
_QWEN_VISION_PREFIXES = (
    "qwen3.6-",
    "qwen3.5-",
    "qwen3-vl-",
    "qwen-vl-",
    "qvq-",
)
_CLAUDE_VISION_PREFIXES = ("claude-3", "claude-sonnet-4", "claude-opus-4", "claude-haiku-4")
_GEMINI_VISION_PREFIXES = ("gemini-",)
_MOONSHOT_VISION_PREFIXES = ("kimi-k2.5", "kimi-k2.6")
_MOONSHOT_VISION_CONTAINS = ("vision-preview",)
_ZHIPU_VISION_PREFIXES = ("glm-5v", "glm-4v", "glm-4.6v", "glm-4.5v", "glm-4.1v")
_DOUBAO_VISION_PREFIXES = (
    "doubao-seed-2-0-pro",
    "doubao-seed-2-0-lite",
    "doubao-seed-2-0-mini",
    "doubao-seed-1-8",
    "doubao-seed-1-6",
    "doubao-1-5-vision",
)
_MINIMAX_VISION_MODELS = {"minimax-text-01", "minimax-vl-01"}


def model_supports_native_image_input(model_name: str, bot_type: str = "") -> bool:
    """Return whether the current chat model should receive image blocks directly."""
    model = (model_name or "").strip().lower()
    if not model:
        return False
    resolved_bot = (bot_type or "").strip()

    if model.startswith(_QWEN_VISION_PREFIXES):
        return True
    if model.startswith(_OPENAI_VISION_PREFIXES):
        return True
    if model.startswith(_CLAUDE_VISION_PREFIXES):
        return True
    if model.startswith(_GEMINI_VISION_PREFIXES):
        return True
    if model.startswith(_MOONSHOT_VISION_PREFIXES) or any(key in model for key in _MOONSHOT_VISION_CONTAINS):
        return True
    if model.startswith(_ZHIPU_VISION_PREFIXES):
        return True
    if model.startswith(_DOUBAO_VISION_PREFIXES) and "code" not in model:
        return True
    if model in _MINIMAX_VISION_MODELS:
        return True

    # Custom OpenAI-compatible endpoints can expose image-capable models under
    # non-standard names.  Only trust the configured provider when the model
    # name itself follows a known vision naming convention.
    if resolved_bot == const.GEMINI and model.startswith(_GEMINI_VISION_PREFIXES):
        return True
    return False


ImageContentBuilder = Callable[[str], dict[str, Any]]


def build_native_image_content(
        user_message: str,
        image_content_builder: ImageContentBuilder | None = None,
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    """
    Convert ``[图片: path]`` markers into structured multimodal content blocks.

    Returns ``(None, [])`` when the message has no image markers or conversion
    fails, allowing the caller to keep the old text + vision-tool fallback path.
    """
    image_refs = [match.group(1).strip() for match in IMAGE_REF_RE.finditer(user_message or "")]
    if not image_refs:
        return None, []

    image_blocks: list[dict[str, Any]] = []
    for image_ref in image_refs:
        image_block = _build_image_block(image_ref, image_content_builder)
        if not image_block:
            return None, []
        image_blocks.append(image_block)

    cleaned_text = IMAGE_REF_RE.sub("", user_message or "").strip()
    if not cleaned_text:
        cleaned_text = "请分析图片内容。"

    # Most native multimodal APIs accept this OpenAI-compatible block shape;
    # provider adapters convert it further where their native shape differs.
    return [*image_blocks, {"type": "text", "text": cleaned_text}], image_refs


def sanitize_images_for_history(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip inline image bytes from persisted/in-memory history after a run."""
    sanitized: list[dict[str, Any]] = []
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            sanitized.append(msg)
            continue

        changed = False
        next_content: list[Any] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "image_url":
                next_content.append({"type": "text", "text": "[图片]"})
                changed = True
            else:
                next_content.append(block)

        sanitized.append({**msg, "content": next_content} if changed else msg)
    return sanitized


def _image_ref_to_url(image_ref: str) -> str:
    if not image_ref:
        return ""
    if image_ref.startswith(("data:", "http://", "https://")):
        return image_ref
    if image_ref.startswith("file://"):
        image_ref = image_ref[len("file://"):]

    path = os.path.expanduser(image_ref)
    if not os.path.isfile(path):
        logger.warning(f"[Multimodal] Image file not found for native input: {image_ref}")
        return ""

    ext = os.path.splitext(path)[1].lower()
    mime_type = SUPPORTED_IMAGE_EXTENSIONS.get(ext) or mimetypes.guess_type(path)[0]
    if not mime_type or not mime_type.startswith("image/"):
        logger.warning(f"[Multimodal] Unsupported image format for native input: {image_ref}")
        return ""

    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime_type};base64,{b64}"
    except Exception as exc:
        logger.warning(f"[Multimodal] Failed to encode image for native input: {exc}")
        return ""


def _build_image_block(
        image_ref: str,
        image_content_builder: ImageContentBuilder | None = None,
) -> dict[str, Any] | None:
    if not image_ref:
        return None
    if image_ref.startswith("data:"):
        return {"type": "image_url", "image_url": {"url": image_ref}}

    if image_content_builder:
        try:
            builder_ref = image_ref[len("file://"):] if image_ref.startswith("file://") else image_ref
            image_block = image_content_builder(builder_ref)
            if _is_image_url_block(image_block):
                return image_block
            logger.warning(f"[Multimodal] Image builder returned invalid block for native input: {image_ref}")
            return None
        except Exception as exc:
            logger.warning(f"[Multimodal] Image builder failed for native input: {exc}")
            return None

    image_url = _image_ref_to_url(image_ref)
    if not image_url:
        return None
    return {"type": "image_url", "image_url": {"url": image_url}}


def _is_image_url_block(block: Any) -> bool:
    if not isinstance(block, dict) or block.get("type") != "image_url":
        return False
    image_url = block.get("image_url", {})
    if isinstance(image_url, dict):
        image_url = image_url.get("url")
    return isinstance(image_url, str) and bool(image_url)
