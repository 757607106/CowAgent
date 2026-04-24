from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
from typing import Any

from cow_platform.deployment import (
    DependencySettings,
    check_all_dependencies,
    validate_environment,
)
from cow_platform.repositories.agent_repository import (
    get_legacy_workspace_root,
)
from cow_platform.repositories.job_repository import JobRepository


class DoctorService:
    """平台自检服务。"""

    REQUIRED_PYTHON_MODULES = ("fastapi", "uvicorn", "click", "web", "psycopg")

    def __init__(self, job_repository: JobRepository | None = None):
        self.job_repository = job_repository or JobRepository()

    @staticmethod
    def _module_exists(name: str) -> bool:
        """检测模块是否可用，兼容测试里注入的简化模块桩。"""
        try:
            return importlib.util.find_spec(name) is not None
        except (ValueError, ImportError):
            return name in sys.modules

    def get_report(self) -> dict[str, Any]:
        workspace_root = get_legacy_workspace_root()
        adr_dir = Path("docs/adr")
        patch_register = Path("docs/patch-register.md")
        upgrade_sop = Path("docs/upstream-upgrade-sop.md")
        compose_base = Path("docker/compose.base.yml")
        compose_platform = Path("docker/compose.platform.yml")

        dependency_settings = DependencySettings.from_env()
        dependency_report = check_all_dependencies(dependency_settings)
        validation_errors = validate_environment(
            dependency_settings,
            strict_secrets=os.getenv("COW_PLATFORM_STRICT_STARTUP", "").lower() in {"1", "true", "yes", "on"},
        )

        checks = {
            "workspace_root": {
                "path": str(workspace_root),
                "exists": workspace_root.exists(),
            },
            **dependency_report["checks"],
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

        warnings = []
        try:
            job_counts = {
                status: len(self.job_repository.list_jobs(status=status, limit=10_000))
                for status in self.job_repository.STATUSES
            }
        except Exception as exc:
            job_counts = {}
            warnings.append(f"postgres_unavailable:{exc}")

        for key in ("adr_dir", "patch_register", "upgrade_sop", "compose_base", "compose_platform"):
            if not checks[key]["exists"]:
                warnings.append(f"missing:{key}")
        for module_name, exists in checks["python_modules"].items():
            if not exists:
                warnings.append(f"missing_module:{module_name}")
        for dependency_name in dependency_report["required"]:
            if not checks[dependency_name]["ok"]:
                warnings.append(f"{dependency_name}_unavailable")
        for error in validation_errors:
            warnings.append(f"deployment_invalid:{error}")

        return {
            "status": "ok" if not warnings else "warn",
            "ready": dependency_report["ok"] and not validation_errors,
            "environment": dependency_settings.environment,
            "required_dependencies": dependency_report["required"],
            "checks": checks,
            "job_counts": job_counts,
            "warnings": warnings,
        }
