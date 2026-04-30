from __future__ import annotations

import argparse
import signal
import threading
import time

from common.log import logger
from config import load_config
from cow_platform.runtime.channel_manager import ChannelManager, set_channel_manager
from cow_platform.services.channel_config_service import ChannelConfigService


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CowAgent tenant channel runtime worker.")
    parser.add_argument("--once", action="store_true", help="同步一次租户渠道运行时后退出。")
    parser.add_argument("--poll-interval", default=15.0, type=float, help="渠道配置轮询间隔（秒）。")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    load_config()

    stop_event = threading.Event()
    manager = ChannelManager()
    set_channel_manager(manager)
    service = ChannelConfigService()

    def _handle_signal(signum, _frame):
        logger.info(f"[ChannelRuntimeWorker] Signal {signum} received, stopping channel runtimes")
        stop_event.set()
        manager.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    def sync_once() -> None:
        definitions = service.list_enabled_runtime_configs()
        manager.sync_channel_configs(definitions)

    sync_once()
    if args.once:
        logger.info("[ChannelRuntimeWorker] Runtime sync completed")
        return

    logger.info("[ChannelRuntimeWorker] Runtime worker started")
    interval = max(1.0, float(args.poll_interval))
    while not stop_event.wait(interval):
        try:
            sync_once()
        except Exception as e:
            logger.warning(f"[ChannelRuntimeWorker] Runtime sync failed: {e}")
            logger.exception(e)
            time.sleep(min(interval, 5.0))


if __name__ == "__main__":
    main()
