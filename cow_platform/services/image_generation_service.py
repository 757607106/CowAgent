from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

from common.log import logger
from config import get_appdata_dir, get_root
from cow_platform.runtime.environment import build_runtime_environment


class ImageGenerationError(RuntimeError):
    """Raised when the image-generation Skill cannot produce an image."""


class ImageGenerationSkillMissing(ImageGenerationError):
    """Raised when the built-in image-generation Skill is not present."""


@dataclass(frozen=True)
class ImageGenerationResult:
    image_path: str
    model: str = ""
    payload: dict[str, Any] | None = None


class ImageGenerationService:
    """Run CowAgent's built-in image-generation Skill under platform runtime config."""

    def __init__(
        self,
        *,
        script_path: str | None = None,
        output_dir: str | None = None,
        python_executable: str | None = None,
        timeout: int = 600,
    ) -> None:
        self.script_path = script_path or os.path.join(
            get_root(),
            "skills",
            "image-generation",
            "scripts",
            "generate.py",
        )
        self.output_dir = output_dir or os.path.join(get_appdata_dir(), "generated_images")
        self.python_executable = python_executable or sys.executable
        self.timeout = timeout

    @staticmethod
    def _build_args(prompt: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        metadata = dict(metadata or {})
        args: dict[str, Any] = {"prompt": prompt}
        if metadata.get("image_size"):
            args["size"] = metadata["image_size"]
        if metadata.get("aspect_ratio"):
            args["aspect_ratio"] = metadata["aspect_ratio"]
        if metadata.get("image_quality"):
            args["quality"] = metadata["image_quality"]
        return args

    @staticmethod
    def _parse_payload(stdout: str) -> dict[str, Any]:
        stdout = (stdout or "").strip()
        if not stdout:
            return {}
        try:
            return json.loads(stdout)
        except Exception:
            match = re.search(r"(\{[\s\S]*\})\s*$", stdout)
            return json.loads(match.group(1)) if match else {}

    def generate(self, prompt: str, *, metadata: dict[str, Any] | None = None) -> ImageGenerationResult:
        if not os.path.isfile(self.script_path):
            raise ImageGenerationSkillMissing("image-generation skill is not installed")

        env = build_runtime_environment(extra_env={"IMAGE_OUTPUT_DIR": self.output_dir})
        args = self._build_args(prompt, metadata)
        proc = subprocess.run(
            [self.python_executable, self.script_path, json.dumps(args, ensure_ascii=False)],
            cwd=get_root(),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout,
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        if proc.returncode != 0:
            logger.error(f"[image_generation_service] skill failed: {stderr or stdout}")
            raise ImageGenerationError("image-generation skill failed")

        payload = self._parse_payload(stdout)
        if payload.get("error"):
            logger.error(f"[image_generation_service] skill error: {payload.get('error')}")
            raise ImageGenerationError(str(payload.get("error")))

        images = payload.get("images") or []
        image_path = (images[0] or {}).get("url") if images else ""
        if not image_path:
            raise ImageGenerationError("image-generation skill returned no image")

        return ImageGenerationResult(
            image_path=image_path,
            model=str(payload.get("model", "") or ""),
            payload=payload,
        )
