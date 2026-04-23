from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cow_platform.domain.models import TenantUserDefinition, TenantUserIdentityDefinition
from cow_platform.repositories.agent_repository import get_platform_data_root


class FileTenantUserRepository:
    """基于 JSON 文件的租户用户与身份映射仓储。"""

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or (get_platform_data_root() / "tenant_users.json")
        self._lock = threading.Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def list_users(
        self,
        *,
        tenant_id: str = "",
        role: str = "",
        status: str = "",
    ) -> list[TenantUserDefinition]:
        with self._lock:
            store = self._load_store()
        users: list[TenantUserDefinition] = []
        for record in store.get("tenant_users", {}).values():
            if tenant_id and record.get("tenant_id") != tenant_id:
                continue
            if role and record.get("role") != role:
                continue
            if status and record.get("status") != status:
                continue
            users.append(self._to_user_definition(record))
        users.sort(key=lambda item: (item.tenant_id, item.user_id))
        return users

    def get_user(self, tenant_id: str, user_id: str) -> TenantUserDefinition | None:
        with self._lock:
            store = self._load_store()
            record = store.get("tenant_users", {}).get(self._build_user_key(tenant_id, user_id))
        if not record:
            return None
        return self._to_user_definition(record)

    def create_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        name: str = "",
        role: str,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> TenantUserDefinition:
        now = int(time.time())
        key = self._build_user_key(tenant_id, user_id)
        with self._lock:
            store = self._load_store()
            if key in store["tenant_users"]:
                raise ValueError(f"tenant user already exists: {tenant_id}/{user_id}")
            record = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "name": name,
                "role": role,
                "status": status,
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now,
            }
            store["tenant_users"][key] = record
            self._save_store(store)
        return self._to_user_definition(record)

    def update_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        name: str | None = None,
        role: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TenantUserDefinition:
        now = int(time.time())
        key = self._build_user_key(tenant_id, user_id)
        with self._lock:
            store = self._load_store()
            record = store["tenant_users"].get(key)
            if not record:
                raise KeyError(f"tenant user not found: {tenant_id}/{user_id}")
            if name is not None:
                record["name"] = name
            if role is not None:
                record["role"] = role
            if status is not None:
                record["status"] = status
            if metadata is not None:
                record["metadata"] = metadata
            record["updated_at"] = now
            self._save_store(store)
        return self._to_user_definition(record)

    def delete_user(self, *, tenant_id: str, user_id: str) -> TenantUserDefinition:
        key = self._build_user_key(tenant_id, user_id)
        with self._lock:
            store = self._load_store()
            record = store["tenant_users"].get(key)
            if not record:
                raise KeyError(f"tenant user not found: {tenant_id}/{user_id}")
            del store["tenant_users"][key]
            identity_keys = [
                identity_key
                for identity_key, identity_record in store.get("identities", {}).items()
                if identity_record.get("tenant_id") == tenant_id and identity_record.get("user_id") == user_id
            ]
            for identity_key in identity_keys:
                del store["identities"][identity_key]
            self._save_store(store)
        return self._to_user_definition(record)

    def list_identities(
        self,
        *,
        tenant_id: str = "",
        user_id: str = "",
        channel_type: str = "",
    ) -> list[TenantUserIdentityDefinition]:
        with self._lock:
            store = self._load_store()
        identities: list[TenantUserIdentityDefinition] = []
        for record in store.get("identities", {}).values():
            if tenant_id and record.get("tenant_id") != tenant_id:
                continue
            if user_id and record.get("user_id") != user_id:
                continue
            if channel_type and record.get("channel_type") != channel_type:
                continue
            identities.append(self._to_identity_definition(record))
        identities.sort(key=lambda item: (item.tenant_id, item.user_id, item.channel_type, item.external_user_id))
        return identities

    def get_identity(
        self,
        *,
        tenant_id: str,
        channel_type: str,
        external_user_id: str,
    ) -> TenantUserIdentityDefinition | None:
        with self._lock:
            store = self._load_store()
            record = store.get("identities", {}).get(
                self._build_identity_key(tenant_id, channel_type, external_user_id)
            )
        if not record:
            return None
        return self._to_identity_definition(record)

    def upsert_identity(
        self,
        *,
        tenant_id: str,
        user_id: str,
        channel_type: str,
        external_user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> TenantUserIdentityDefinition:
        now = int(time.time())
        user_key = self._build_user_key(tenant_id, user_id)
        identity_key = self._build_identity_key(tenant_id, channel_type, external_user_id)
        with self._lock:
            store = self._load_store()
            if user_key not in store["tenant_users"]:
                raise KeyError(f"tenant user not found: {tenant_id}/{user_id}")
            existing = store["identities"].get(identity_key)
            if existing and existing.get("user_id") != user_id:
                raise ValueError(
                    "identity already bound to another tenant user: "
                    f"{tenant_id}/{channel_type}/{external_user_id}"
                )
            if existing:
                existing["user_id"] = user_id
                existing["metadata"] = metadata or {}
                existing["updated_at"] = now
                record = existing
            else:
                record = {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "channel_type": channel_type,
                    "external_user_id": external_user_id,
                    "metadata": metadata or {},
                    "created_at": now,
                    "updated_at": now,
                }
            store["identities"][identity_key] = record
            self._save_store(store)
        return self._to_identity_definition(record)

    def delete_identity(
        self,
        *,
        tenant_id: str,
        channel_type: str,
        external_user_id: str,
    ) -> TenantUserIdentityDefinition:
        identity_key = self._build_identity_key(tenant_id, channel_type, external_user_id)
        with self._lock:
            store = self._load_store()
            record = store["identities"].get(identity_key)
            if not record:
                raise KeyError(f"identity not found: {tenant_id}/{channel_type}/{external_user_id}")
            del store["identities"][identity_key]
            self._save_store(store)
        return self._to_identity_definition(record)

    def find_user_by_identity(
        self,
        *,
        tenant_id: str,
        channel_type: str,
        external_user_id: str,
    ) -> TenantUserDefinition | None:
        with self._lock:
            store = self._load_store()
            identity = store.get("identities", {}).get(
                self._build_identity_key(tenant_id, channel_type, external_user_id)
            )
            if not identity:
                return None
            user_record = store.get("tenant_users", {}).get(
                self._build_user_key(tenant_id, str(identity.get("user_id", "")))
            )
        if not user_record:
            return None
        return self._to_user_definition(user_record)

    def export_user_record(self, definition: TenantUserDefinition) -> dict[str, Any]:
        record = asdict(definition)
        with self._lock:
            store = self._load_store()
            saved = store.get("tenant_users", {}).get(self._build_user_key(definition.tenant_id, definition.user_id), {})
        record["created_at"] = saved.get("created_at")
        record["updated_at"] = saved.get("updated_at")
        return record

    def export_identity_record(self, definition: TenantUserIdentityDefinition) -> dict[str, Any]:
        record = asdict(definition)
        with self._lock:
            store = self._load_store()
            saved = store.get("identities", {}).get(
                self._build_identity_key(definition.tenant_id, definition.channel_type, definition.external_user_id),
                {},
            )
        record["created_at"] = saved.get("created_at")
        record["updated_at"] = saved.get("updated_at")
        return record

    @staticmethod
    def _build_user_key(tenant_id: str, user_id: str) -> str:
        return f"{tenant_id}:{user_id}"

    @staticmethod
    def _build_identity_key(tenant_id: str, channel_type: str, external_user_id: str) -> str:
        return f"{tenant_id}:{channel_type}:{external_user_id}"

    def _load_store(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"tenant_users": {}, "identities": {}}
        with self.store_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if "tenant_users" not in data:
            data["tenant_users"] = {}
        if "identities" not in data:
            data["identities"] = {}
        return data

    def _save_store(self, store: dict[str, Any]) -> None:
        with self.store_path.open("w", encoding="utf-8") as file:
            json.dump(store, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_user_definition(record: dict[str, Any]) -> TenantUserDefinition:
        return TenantUserDefinition(
            tenant_id=record["tenant_id"],
            user_id=record["user_id"],
            name=record.get("name", ""),
            role=record.get("role", "member"),
            status=record.get("status", "active"),
            metadata=record.get("metadata", {}) or {},
        )

    @staticmethod
    def _to_identity_definition(record: dict[str, Any]) -> TenantUserIdentityDefinition:
        return TenantUserIdentityDefinition(
            tenant_id=record["tenant_id"],
            user_id=record["user_id"],
            channel_type=record["channel_type"],
            external_user_id=record["external_user_id"],
            metadata=record.get("metadata", {}) or {},
        )
