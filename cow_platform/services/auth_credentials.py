from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Any, Iterable, TypeVar


PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260000

_T = TypeVar("_T")


def normalize_account(account: str) -> str:
    return (account or "").strip().lower()


def validate_password(password: str) -> None:
    if len(password or "") < 8:
        raise ValueError("password must be at least 8 characters")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"{PASSWORD_HASH_SCHEME}${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


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


def build_auth_metadata(*, account: str, password: str) -> dict[str, Any]:
    validate_password(password)
    resolved_account = normalize_account(account)
    metadata: dict[str, Any] = {
        "password_hash": hash_password(password),
        "created_at": int(time.time()),
    }
    if resolved_account:
        metadata["account"] = resolved_account
    return metadata


def get_password_hash(metadata: Any) -> str:
    auth_meta = get_auth_metadata(metadata)
    return str(auth_meta.get("password_hash", "") or "") if auth_meta else ""


def get_auth_account(metadata: Any) -> str:
    auth_meta = get_auth_metadata(metadata)
    return str(auth_meta.get("account", "") or "") if auth_meta else ""


def get_auth_metadata(metadata: Any) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    auth_meta = metadata.get("auth")
    return auth_meta if isinstance(auth_meta, dict) else {}


def sanitize_user_record(record: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(record)
    metadata = dict(cleaned.get("metadata") or {})
    auth_meta = metadata.get("auth")
    if isinstance(auth_meta, dict):
        metadata["auth_enabled"] = bool(auth_meta.get("password_hash"))
        metadata.pop("auth", None)
    cleaned["metadata"] = metadata
    return cleaned


def find_by_account(users: Iterable[_T], account: str) -> list[_T]:
    resolved_account = normalize_account(account)
    return [
        user
        for user in users
        if get_auth_account(getattr(user, "metadata", {})) == resolved_account
    ]
