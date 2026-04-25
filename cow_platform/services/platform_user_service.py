from __future__ import annotations

import re
import secrets
from typing import Any

from cow_platform.domain.models import PlatformUserDefinition
from cow_platform.repositories.platform_user_repository import PlatformUserRepository
from cow_platform.services.auth_credentials import (
    build_auth_metadata,
    find_by_account,
    get_auth_account,
    normalize_account,
    sanitize_user_record,
    validate_password,
)


PLATFORM_SUPER_ADMIN_ROLE = "platform_super_admin"
PLATFORM_USER_STATUSES: tuple[str, ...] = ("active", "disabled")


class PlatformUserService:
    """平台级用户管理服务。"""

    def __init__(
        self,
        repository: PlatformUserRepository | None = None,
        tenant_user_service: Any | None = None,
    ):
        self.repository = repository or PlatformUserRepository()
        self.tenant_user_service = tenant_user_service

    def list_users(self, *, role: str = "", status: str = "") -> list[PlatformUserDefinition]:
        return self.repository.list_users(role=role, status=status)

    def has_platform_admin(self) -> bool:
        return any(
            user.role == PLATFORM_SUPER_ADMIN_ROLE
            for user in self.repository.list_users(role=PLATFORM_SUPER_ADMIN_ROLE)
        )

    def resolve_user(self, user_id: str) -> PlatformUserDefinition:
        definition = self.repository.get_user((user_id or "").strip())
        if definition is None:
            raise KeyError(f"platform user not found: {user_id}")
        return definition

    def create_platform_admin(
        self,
        *,
        account: str,
        password: str,
        name: str = "",
        user_id: str = "",
    ) -> dict[str, Any]:
        resolved_account = normalize_account(account)
        if not resolved_account:
            raise ValueError("account must not be empty")

        validate_password(password)
        if self._find_users_by_account(resolved_account) or self._find_tenant_users_by_account(resolved_account):
            raise ValueError("account already registered")

        resolved_user_id = (user_id or "").strip() or self._generate_user_id(resolved_account)
        definition = self.repository.create_user(
            user_id=resolved_user_id,
            name=(name or "").strip() or resolved_account,
            role=PLATFORM_SUPER_ADMIN_ROLE,
            status="active",
            metadata={"auth": build_auth_metadata(account=resolved_account, password=password)},
        )
        return self.serialize_user(definition)

    def serialize_user(self, definition: PlatformUserDefinition) -> dict[str, Any]:
        return self._sanitize_user_record(self.repository.export_user_record(definition))

    def list_user_records(self, *, role: str = "", status: str = "") -> list[dict[str, Any]]:
        return [self.serialize_user(user) for user in self.list_users(role=role, status=status)]

    @staticmethod
    def _normalize_account(account: str) -> str:
        return normalize_account(account)

    @staticmethod
    def _get_auth_account(metadata: Any) -> str:
        return get_auth_account(metadata)

    def _find_users_by_account(self, account: str) -> list[PlatformUserDefinition]:
        return find_by_account(self.repository.list_users(), account)

    def _find_tenant_users_by_account(self, account: str) -> list[Any]:
        try:
            tenant_user_service = self.tenant_user_service
            if tenant_user_service is None:
                from cow_platform.services.tenant_user_service import TenantUserService

                tenant_user_service = TenantUserService()
            return find_by_account(tenant_user_service.list_users(), account)
        except Exception:
            return []

    def _generate_user_id(self, account: str) -> str:
        for _ in range(50):
            slug = re.sub(r"[^a-z0-9]+", "-", account.lower()).strip("-")[:24].strip("-")
            suffix = secrets.token_hex(4)
            candidate = f"platform-{slug}-{suffix}" if slug else f"platform-{suffix}"
            if self.repository.get_user(candidate) is None:
                return candidate
        raise RuntimeError("failed to generate platform user id")

    @staticmethod
    def _sanitize_user_record(record: dict[str, Any]) -> dict[str, Any]:
        return sanitize_user_record(record)
