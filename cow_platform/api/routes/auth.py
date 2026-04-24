from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request

from cow_platform.api.schemas import TenantLoginRequest, TenantRegisterRequest
from cow_platform.services.auth_service import TenantAuthService


def register_auth_routes(app: FastAPI, *, auth_service: TenantAuthService) -> None:
    @app.post("/api/platform/auth/register")
    def register_tenant(payload: TenantRegisterRequest) -> dict[str, object]:
        try:
            result = auth_service.register_tenant(
                tenant_id=payload.tenant_id,
                tenant_name=payload.tenant_name,
                user_id=payload.user_id,
                account=payload.account,
                name=payload.user_name,
                password=payload.password,
            )
            if payload.account:
                session = auth_service.authenticate_account(
                    account=payload.account,
                    password=payload.password,
                )
            else:
                session = auth_service.authenticate(
                    tenant_id=result["tenant"]["tenant_id"],
                    user_id=result["tenant_user"]["user_id"],
                    password=payload.password,
                )
            return {
                "status": "success",
                **result,
                "user": session.to_public_dict(),
                "token": auth_service.create_session_token(session),
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/platform/auth/login")
    def login(payload: TenantLoginRequest) -> dict[str, object]:
        try:
            if payload.account:
                session = auth_service.authenticate_account(
                    account=payload.account,
                    password=payload.password,
                )
            else:
                session = auth_service.authenticate(
                    tenant_id=payload.tenant_id,
                    user_id=payload.user_id,
                    password=payload.password,
                )
        except Exception as exc:
            raise HTTPException(status_code=401, detail="invalid account or password") from exc
        return {
            "status": "success",
            "user": session.to_public_dict(),
            "token": auth_service.create_session_token(session),
        }

    @app.get("/api/platform/auth/me")
    def me(request: Request) -> dict[str, object]:
        auth_header = request.headers.get("authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        session = auth_service.verify_session_token(token)
        if session is None:
            raise HTTPException(status_code=401, detail="unauthorized")
        return {"status": "success", "user": session.to_public_dict()}
