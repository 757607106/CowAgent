# encoding:utf-8

import signal
import sys
import time

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
