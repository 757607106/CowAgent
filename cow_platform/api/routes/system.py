from __future__ import annotations

from fastapi import FastAPI, Request

from cow_platform.api.security import PlatformAuthorizer
from cow_platform.services.doctor_service import DoctorService


def register_system_routes(
    app: FastAPI,
    *,
    mode: str,
    doctor_service: DoctorService,
    authorizer: PlatformAuthorizer,
) -> None:
    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "cow-platform",
            "mode": mode,
        }

    @app.get("/ready")
    def ready() -> dict[str, object]:
        report = doctor_service.get_report()
        dependencies = {
            name: report["checks"][name]
            for name in ("postgres", "redis", "qdrant", "minio")
            if name in report["checks"]
        }
        return {
            "status": "ready" if report.get("ready") else "degraded",
            "service": "cow-platform",
            "environment": report.get("environment"),
            "required_dependencies": report.get("required_dependencies", []),
            "dependencies": dependencies,
            "warnings": report.get("warnings", []),
        }

    @app.get("/api/platform/doctor")
    def get_doctor_report(request: Request) -> dict[str, object]:
        authorizer.require_session(request)
        return {
            "status": "success",
            "report": doctor_service.get_report(),
        }
