from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any

from cow_platform.repositories.agent_repository import (
    get_legacy_workspace_root,
    get_platform_data_root,
)
from cow_platform.repositories.job_repository import FileJobRepository


class DoctorService:
    """平台自检服务。"""

    REQUIRED_PYTHON_MODULES = ("fastapi", "uvicorn", "click", "web")

    def __init__(self, job_repository: FileJobRepository | None = None):
        self.job_repository = job_repository or FileJobRepository()

    @staticmethod
    def _module_exists(name: str) -> bool:
        """检测模块是否可用，兼容测试里注入的简化模块桩。"""
        try:
            return importlib.util.find_spec(name) is not None
        except (ValueError, ImportError):
            return name in sys.modules

    def get_report(self) -> dict[str, Any]:
        workspace_root = get_legacy_workspace_root()
        data_root = get_platform_data_root()
        adr_dir = Path("docs/adr")
        patch_register = Path("docs/patch-register.md")
        upgrade_sop = Path("docs/upstream-upgrade-sop.md")
        compose_base = Path("docker/compose.base.yml")
        compose_platform = Path("docker/compose.platform.yml")

        checks = {
            "workspace_root": {
                "path": str(workspace_root),
                "exists": workspace_root.exists(),
            },
            "platform_data_root": {
                "path": str(data_root),
                "exists": data_root.exists(),
            },
            "adr_dir": {
                "path": str(adr_dir),
                "exists": adr_dir.exists(),
            },
            "patch_register": {
                "path": str(patch_register),
                "exists": patch_register.exists(),
            },
            "upgrade_sop": {
                "path": str(upgrade_sop),
                "exists": upgrade_sop.exists(),
            },
            "compose_base": {
                "path": str(compose_base),
                "exists": compose_base.exists(),
            },
            "compose_platform": {
                "path": str(compose_platform),
                "exists": compose_platform.exists(),
            },
            "python_modules": {
                name: self._module_exists(name)
                for name in self.REQUIRED_PYTHON_MODULES
            },
        }

        job_counts = {
            status: len(self.job_repository.list_jobs(status=status, limit=10_000))
            for status in self.job_repository.STATUSES
        }

        warnings = []
        for key in ("adr_dir", "patch_register", "upgrade_sop", "compose_base", "compose_platform"):
            if not checks[key]["exists"]:
                warnings.append(f"missing:{key}")
        for module_name, exists in checks["python_modules"].items():
            if not exists:
                warnings.append(f"missing_module:{module_name}")

        return {
            "status": "ok" if not warnings else "warn",
            "checks": checks,
            "job_counts": job_counts,
            "warnings": warnings,
        }
