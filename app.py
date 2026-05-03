# encoding:utf-8

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from common.log import logger
from config import conf, load_config
from cow_platform.runtime import channel_manager as _channel_manager_module
from cow_platform.runtime.channel_manager import (
    ChannelManager,
    _clear_singleton_cache,
    _resolve_startup_channels,
    get_channel_manager as _runtime_get_channel_manager,
    set_channel_manager,
)


# Backward-compatible module attributes used by legacy helpers and tests.
channel_factory = _channel_manager_module.channel_factory
_channel_mgr = None


_LOCAL_PLATFORM_ENV_KEYS = {
    "AGENT_WORKSPACE",
    "MODEL",
    "WEB_PORT",
    "WEB_TENANT_AUTH",
}


def _is_false_env(value: str) -> bool:
    return value.strip().lower() in {"0", "false", "no", "off"}


def _should_import_local_platform_env(root: Path) -> bool:
    if _is_false_env(os.environ.get("COW_PLATFORM_AUTO_LOCAL_ENV", "true")):
        return False
    return (root / ".env.local").is_file()


def _parse_null_separated_env(raw_env: bytes) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in raw_env.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        values[key.decode("utf-8")] = value.decode("utf-8")
    return values


def _import_local_platform_env(root: Path | None = None) -> None:
    root = root or Path(__file__).resolve().parent
    if not _should_import_local_platform_env(root):
        return

    result = subprocess.run(
        ["/bin/bash", "-lc", "set -a; source .env.local; set +a; env -0"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Failed to load local platform env from .env.local: {message}")

    loaded_env = _parse_null_separated_env(result.stdout)
    imported = 0
    for key, value in loaded_env.items():
        if key.startswith(("COW_PLATFORM_", "PLATFORM_")) or key in _LOCAL_PLATFORM_ENV_KEYS:
            os.environ[key] = value
            imported += 1

    logger.info(
        "[App] Loaded local platform env from .env.local: WEB_PORT={}, MODEL={}, AGENT_WORKSPACE={}".format(
            os.environ.get("WEB_PORT", ""),
            os.environ.get("MODEL", ""),
            os.environ.get("AGENT_WORKSPACE", ""),
        )
    )
    logger.debug("[App] Imported {} local platform environment variables".format(imported))


def get_channel_manager():
    return _runtime_get_channel_manager()


def sigterm_handler_wrap(_signo):
    old_handler = signal.getsignal(_signo)

    def func(_signo, _stack_frame):
        logger.info("signal {} received, exiting...".format(_signo))
        conf().save_user_datas()
        if callable(old_handler):
            return old_handler(_signo, _stack_frame)
        sys.exit(0)

    signal.signal(_signo, func)


def run():
    global _channel_mgr
    try:
        _import_local_platform_env()
        load_config()
        sigterm_handler_wrap(signal.SIGINT)
        sigterm_handler_wrap(signal.SIGTERM)

        web_console_enabled = conf().get("web_console", True)
        channel_names = _resolve_startup_channels(
            web_console_enabled=web_console_enabled,
            command_mode="--cmd" in sys.argv,
        )

        logger.info(f"[App] Starting channels: {channel_names}")

        _channel_mgr = ChannelManager()
        set_channel_manager(_channel_mgr)
        _channel_mgr.start(channel_names, first_start=True)
        if conf().get("platform_start_channel_runtimes", False):
            try:
                from cow_platform.services.channel_config_service import ChannelConfigService

                _channel_mgr.start_channel_configs(ChannelConfigService().list_enabled_runtime_configs())
            except Exception as e:
                logger.warning(f"[App] Failed to auto-start tenant channel configs: {e}")
        else:
            logger.info("[App] Tenant channel runtimes are disabled in web process; use cow platform channel-runtime")

        while True:
            time.sleep(1)
    except Exception as e:
        logger.error("App startup failed!")
        logger.exception(e)


if __name__ == "__main__":
    run()
