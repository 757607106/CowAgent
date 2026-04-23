from __future__ import annotations

import os
from dataclasses import dataclass, replace

DEFAULT_PLATFORM_HOST = "127.0.0.1"
DEFAULT_PLATFORM_PORT = 9900
DEFAULT_PLATFORM_MODE = "platform"


@dataclass(frozen=True, slots=True)
class PlatformSettings:
    host: str = DEFAULT_PLATFORM_HOST
    port: int = DEFAULT_PLATFORM_PORT
    mode: str = DEFAULT_PLATFORM_MODE

    @classmethod
    def from_env(cls) -> "PlatformSettings":
        return cls(
            host=os.getenv("COW_PLATFORM_HOST", DEFAULT_PLATFORM_HOST),
            port=int(os.getenv("COW_PLATFORM_PORT", str(DEFAULT_PLATFORM_PORT))),
            mode=os.getenv("COW_PLATFORM_MODE", DEFAULT_PLATFORM_MODE),
        )

    def with_overrides(self, host: str | None = None, port: int | None = None) -> "PlatformSettings":
        return replace(
            self,
            host=host or self.host,
            port=port if port is not None else self.port,
        )
