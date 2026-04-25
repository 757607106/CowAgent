from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass
from typing import Any

from cow_platform.db import connect
from cow_platform.services.agent_service import AgentService
from cow_platform.services.platform_user_service import PLATFORM_SUPER_ADMIN_ROLE, PlatformUserService
from cow_platform.services.tenant_service import TenantService
from cow_platform.services.tenant_user_service import TenantUserService


PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260000


@dataclass(frozen=True, slots=True)
class TenantAuthSession:
    tenant_id: str
    user_id: str
    role: str
    expires_at: int
    principal_type: str = "tenant"
    tenant_name: str = ""
    user_name: str = ""
    account: str = ""

    def to_public_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "role": self.role,
            "expires_at": self.expires_at,
            "principal_type": self.principal_type,
        }
        if self.tenant_name:
            data["tenant_name"] = self.tenant_name
        if self.user_name:
            data["user_name"] = self.user_name
        if self.account:
            data["account"] = self.account
        return data


class TenantAuthService:
    """租户注册、用户登录与会话签名服务。"""

    def __init__(
        self,
        *,
        tenant_service: TenantService | None = None,
        tenant_user_service: TenantUserService | None = None,
        agent_service: AgentService | None = None,
        platform_user_service: PlatformUserService | None = None,
        session_expire_seconds: int = 30 * 86400,
    ):
        self.tenant_service = tenant_service or TenantService()
        self.tenant_user_service = tenant_user_service or TenantUserService(
            tenant_service=self.tenant_service,
        )
        self.agent_service = agent_service or AgentService(tenant_service=self.tenant_service)
        self.platform_user_service = platform_user_service or PlatformUserService()
        self.session_expire_seconds = session_expire_seconds

    def register_platform_admin(
        self,
        *,
        account: str,
        password: str,
        name: str = "",
    ) -> dict[str, Any]:
        resolved_account = self._normalize_account(account)
        if not resolved_account:
            raise ValueError("account must not be empty")
        if self.has_platform_admin():
            raise ValueError("platform admin already exists")
        self._validate_password(password)
        self._ensure_account_available(resolved_account)
        return {
            "platform_user": self.platform_user_service.create_platform_admin(
                account=resolved_account,
                password=password,
                name=name,
            )
        }

    def register_tenant(
        self,
        *,
        tenant_id: str = "",
        tenant_name: str,
        user_id: str = "",
        password: str,
        name: str = "",
        account: str = "",
    ) -> dict[str, Any]:
        resolved_tenant_name = self._normalize_required("tenant_name", tenant_name)
        resolved_account = self._normalize_account(account)
        self._validate_password(password)
        if not resolved_account and not ((tenant_id or "").strip() and (user_id or "").strip()):
            raise ValueError("account must not be empty")
        if resolved_account:
            self._ensure_account_available(resolved_account)

        resolved_tenant_id = (tenant_id or "").strip() or self._generate_unique_tenant_id(resolved_tenant_name)

        tenant = self.tenant_service.create_tenant(
            tenant_id=resolved_tenant_id,
            name=resolved_tenant_name,
            status="active",
            metadata={"source": "tenant-register"},
        )
        resolved_user_id = (user_id or "").strip() or self._generate_unique_user_id(
            tenant_id=resolved_tenant_id,
            seed=resolved_account or name or "owner",
        )
        auth_metadata = {
            "password_hash": self.hash_password(password),
            "created_at": int(time.time()),
        }
        if resolved_account:
            auth_metadata["account"] = resolved_account
        user = self.tenant_user_service.create_user(
            tenant_id=resolved_tenant_id,
            user_id=resolved_user_id,
            name=(name or "").strip() or resolved_account or resolved_user_id,
            role="owner",
            status="active",
            metadata={"auth": auth_metadata},
        )
        default_agent = self.agent_service.ensure_default_agent(resolved_tenant_id)
        return {
            "tenant": tenant,
            "tenant_user": user,
            "default_agent": self.agent_service.serialize_agent(default_agent),
        }

    def authenticate(self, *, tenant_id: str, user_id: str, password: str) -> TenantAuthSession:
        resolved_tenant_id = self._normalize_required("tenant_id", tenant_id)
        resolved_user_id = self._normalize_required("user_id", user_id)

        tenant = self.tenant_service.resolve_tenant(resolved_tenant_id)
        if tenant.status != "active":
            raise PermissionError("tenant is not active")

        user = self.tenant_user_service.resolve_user(
            tenant_id=resolved_tenant_id,
            user_id=resolved_user_id,
        )
        if user.status != "active":
            raise PermissionError("tenant user is not active")

        password_hash = self._get_password_hash(user.metadata)
        if not password_hash or not self.verify_password(password, password_hash):
            raise PermissionError("invalid tenant_id, user_id or password")

        return self._build_session(tenant=tenant, user=user)

    def authenticate_account(self, *, account: str, password: str) -> TenantAuthSession:
        resolved_account = self._normalize_required("account", self._normalize_account(account))
        platform_matches = self._find_platform_users_by_account(resolved_account)
        if platform_matches:
            if len(platform_matches) != 1:
                raise PermissionError("invalid account or password")
            platform_user = platform_matches[0]
            if platform_user.status != "active" or platform_user.role != PLATFORM_SUPER_ADMIN_ROLE:
                raise PermissionError("invalid account or password")
            password_hash = self._get_password_hash(platform_user.metadata)
            if not password_hash or not self.verify_password(password, password_hash):
                raise PermissionError("invalid account or password")
            return self._build_platform_session(platform_user)

        matches = self._find_users_by_account(resolved_account)
        if len(matches) != 1:
            raise PermissionError("invalid account or password")

        user = matches[0]
        tenant = self.tenant_service.resolve_tenant(user.tenant_id)
        if tenant.status != "active" or user.status != "active":
            raise PermissionError("invalid account or password")

        password_hash = self._get_password_hash(user.metadata)
        if not password_hash or not self.verify_password(password, password_hash):
            raise PermissionError("invalid account or password")

        return self._build_session(tenant=tenant, user=user)

    def has_credentials(self) -> bool:
        for user in self.tenant_user_service.list_users():
            if self._get_password_hash(user.metadata):
                return True
        return False

    def has_platform_admin(self) -> bool:
        return self.platform_user_service.has_platform_admin()

    def create_session_token(self, session: TenantAuthSession) -> str:
        payload = {
            "tenant_id": session.tenant_id,
            "user_id": session.user_id,
            "role": session.role,
            "principal_type": session.principal_type,
            "exp": session.expires_at,
            "iat": int(time.time()),
        }
        payload_b64 = self._b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = hmac.new(
            self._get_signing_secret(),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        return f"{payload_b64}.{signature}"

    def verify_session_token(self, token: str) -> TenantAuthSession | None:
        if not token or "." not in token:
            return None
        payload_b64, signature = token.rsplit(".", 1)
        expected = hmac.new(
            self._get_signing_secret(),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        try:
            payload = json.loads(self._b64decode(payload_b64))
        except Exception:
            return None

        expires_at = int(payload.get("exp") or 0)
        if expires_at <= int(time.time()):
            return None

        principal_type = str(payload.get("principal_type", "tenant") or "tenant").strip() or "tenant"
        tenant_id = str(payload.get("tenant_id", "")).strip()
        user_id = str(payload.get("user_id", "")).strip()
        role = str(payload.get("role", "")).strip()
        if not user_id or not role:
            return None

        if principal_type == "platform":
            try:
                platform_user = self.platform_user_service.resolve_user(user_id)
            except Exception:
                return None
            if platform_user.status != "active" or platform_user.role != PLATFORM_SUPER_ADMIN_ROLE:
                return None
            return TenantAuthSession(
                tenant_id="",
                user_id=platform_user.user_id,
                role=platform_user.role,
                expires_at=expires_at,
                principal_type="platform",
                user_name=platform_user.name,
                account=self._get_auth_account(platform_user.metadata),
            )

        if not tenant_id:
            return None

        try:
            tenant = self.tenant_service.resolve_tenant(tenant_id)
            user = self.tenant_user_service.resolve_user(tenant_id=tenant_id, user_id=user_id)
        except Exception:
            return None
        if tenant.status != "active" or user.status != "active":
            return None

        return TenantAuthSession(
            tenant_id=tenant_id,
            user_id=user_id,
            role=user.role,
            expires_at=expires_at,
            principal_type="tenant",
            tenant_name=tenant.name,
            user_name=user.name,
            account=self._get_auth_account(user.metadata),
        )

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            PASSWORD_ITERATIONS,
        )
        return (
            f"{PASSWORD_HASH_SCHEME}${PASSWORD_ITERATIONS}$"
            f"{salt.hex()}${digest.hex()}"
        )

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        try:
            scheme, iterations_text, salt_hex, digest_hex = password_hash.split("$", 3)
            if scheme != PASSWORD_HASH_SCHEME:
                return False
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations_text),
            )
            return hmac.compare_digest(digest.hex(), digest_hex)
        except Exception:
            return False

    @staticmethod
    def sanitize_user_record(record: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(record)
        metadata = dict(cleaned.get("metadata") or {})
        auth_meta = metadata.get("auth")
        if isinstance(auth_meta, dict):
            metadata["auth_enabled"] = bool(auth_meta.get("password_hash"))
            metadata.pop("auth", None)
        cleaned["metadata"] = metadata
        return cleaned

    @staticmethod
    def _get_password_hash(metadata: Any) -> str:
        if not isinstance(metadata, dict):
            return ""
        auth_meta = metadata.get("auth")
        if not isinstance(auth_meta, dict):
            return ""
        return str(auth_meta.get("password_hash", "") or "")

    @staticmethod
    def _get_auth_account(metadata: Any) -> str:
        if not isinstance(metadata, dict):
            return ""
        auth_meta = metadata.get("auth")
        if not isinstance(auth_meta, dict):
            return ""
        return str(auth_meta.get("account", "") or "")

    @staticmethod
    def _normalize_account(account: str) -> str:
        return (account or "").strip().lower()

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password or "") < 8:
            raise ValueError("password must be at least 8 characters")

    @staticmethod
    def _normalize_required(name: str, value: str) -> str:
        resolved = (value or "").strip()
        if not resolved:
            raise ValueError(f"{name} must not be empty")
        return resolved

    def _build_session(self, *, tenant: Any, user: Any) -> TenantAuthSession:
        return TenantAuthSession(
            tenant_id=tenant.tenant_id,
            user_id=user.user_id,
            role=user.role,
            expires_at=int(time.time()) + self.session_expire_seconds,
            principal_type="tenant",
            tenant_name=tenant.name,
            user_name=user.name,
            account=self._get_auth_account(user.metadata),
        )

    def _build_platform_session(self, platform_user: Any) -> TenantAuthSession:
        return TenantAuthSession(
            tenant_id="",
            user_id=platform_user.user_id,
            role=platform_user.role,
            expires_at=int(time.time()) + self.session_expire_seconds,
            principal_type="platform",
            user_name=platform_user.name,
            account=self._get_auth_account(platform_user.metadata),
        )

    def _ensure_account_available(self, account: str) -> None:
        if self._find_users_by_account(account) or self._find_platform_users_by_account(account):
            raise ValueError("account already registered")

    def _find_users_by_account(self, account: str) -> list[Any]:
        return [
            user
            for user in self.tenant_user_service.list_users()
            if self._get_auth_account(user.metadata) == account
        ]

    def _find_platform_users_by_account(self, account: str) -> list[Any]:
        return [
            user
            for user in self.platform_user_service.list_users()
            if self._get_auth_account(user.metadata) == account
        ]

    def _generate_unique_tenant_id(self, tenant_name: str) -> str:
        for _ in range(50):
            candidate = self._make_generated_id("tenant", tenant_name)
            if not self._tenant_exists(candidate):
                return candidate
        raise RuntimeError("failed to generate tenant id")

    def _generate_unique_user_id(self, *, tenant_id: str, seed: str) -> str:
        for _ in range(50):
            candidate = self._make_generated_id("user", seed)
            if not self._user_exists(tenant_id=tenant_id, user_id=candidate):
                return candidate
        raise RuntimeError("failed to generate user id")

    def _tenant_exists(self, tenant_id: str) -> bool:
        try:
            self.tenant_service.resolve_tenant(tenant_id)
            return True
        except KeyError:
            return False

    def _user_exists(self, *, tenant_id: str, user_id: str) -> bool:
        try:
            self.tenant_user_service.resolve_user(tenant_id=tenant_id, user_id=user_id)
            return True
        except KeyError:
            return False

    @staticmethod
    def _make_generated_id(prefix: str, seed: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", (seed or "").lower()).strip("-")[:24].strip("-")
        suffix = secrets.token_hex(4)
        return f"{prefix}-{slug}-{suffix}" if slug else f"{prefix}-{suffix}"

    @staticmethod
    def _b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    @staticmethod
    def _b64decode(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)

    def _get_signing_secret(self) -> bytes:
        with connect() as conn:
            row = conn.execute(
                "SELECT value FROM platform_settings WHERE key = %s",
                ("auth_signing_secret",),
            ).fetchone()
            if row:
                return str(row["value"]).encode("utf-8")
            secret = secrets.token_urlsafe(48)
            conn.execute(
                """
                INSERT INTO platform_settings (key, value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO NOTHING
                """,
                ("auth_signing_secret", secret, int(time.time())),
            )
            conn.commit()
            row = conn.execute(
                "SELECT value FROM platform_settings WHERE key = %s",
                ("auth_signing_secret",),
            ).fetchone()
        return str(row["value"] if row else secret).encode("utf-8")
