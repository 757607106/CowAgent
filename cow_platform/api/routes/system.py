from __future__ import annotations

from fastapi import FastAPI

from cow_platform.services.doctor_service import DoctorService


def register_system_routes(
    app: FastAPI,
    *,
    mode: str,
    doctor_service: DoctorService,
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
        return {
            "status": "ready",
            "service": "cow-platform",
            "dependencies": {},
        }

    @app.get("/api/platform/doctor")
    def get_doctor_report() -> dict[str, object]:
        return {
            "status": "success",
            "report": doctor_service.get_report(),
        }
