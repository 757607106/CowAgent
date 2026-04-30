from __future__ import annotations

import os
import threading
import time

from channel import channel_factory
from common import const
from common.log import logger
from config import conf
from plugins import PluginManager


_channel_mgr = None


def get_channel_manager():
    return _channel_mgr


def set_channel_manager(manager) -> None:
    global _channel_mgr
    _channel_mgr = manager


def _resolve_startup_channels(
    *,
    web_console_enabled: bool,
    command_mode: bool = False,
) -> list:
    if command_mode:
        return ["terminal"]

    # 平台多租户模式只在启动配置里保留 Web 控制台；微信、飞书等托管渠道随后从数据库按 channel_config_id 启动。
    return ["web"] if web_console_enabled else []


class ChannelManager:
    """
    Manage the lifecycle of local and tenant channel runtimes.

    Web/API processes should normally start only the web console. Tenant long
    connections and polling channels are owned by the platform runtime worker.
    """

    def __init__(self):
        self._channels = {}
        self._threads = {}
        self._lease_stop_events = {}
        self._lease_threads = {}
        self._primary_channel = None
        self._lock = threading.Lock()
        self.cloud_mode = False
        from cow_platform.services.channel_runtime_service import ChannelRuntimeLeaseService

        self._runtime_leases = ChannelRuntimeLeaseService()

    @property
    def channel(self):
        """Return the primary channel for backward compatibility."""
        return self._primary_channel

    def get_channel(self, channel_name: str):
        return self._channels.get(channel_name)

    def get_channel_config(self, channel_config_id: str):
        return self._channels.get(channel_config_id)

    def list_channel_config_ids(self) -> list[str]:
        with self._lock:
            return [
                name
                for name, channel in self._channels.items()
                if getattr(channel, "channel_config_id", "") == name
            ]

    def start(self, channel_names: list, first_start: bool = False):
        """
        Create and start one or more channels in daemon threads.
        """
        with self._lock:
            channels = []
            for name in channel_names:
                ch = channel_factory.create_channel(name)
                ch.cloud_mode = self.cloud_mode
                self._channels[name] = ch
                channels.append((name, ch))
                if self._primary_channel is None and name != "web":
                    self._primary_channel = ch

            if self._primary_channel is None and channels:
                self._primary_channel = channels[0][1]

            if first_start:
                PluginManager().load_plugins()

                if conf().get("use_linkai") and (
                    os.environ.get("CLOUD_DEPLOYMENT_ID") or conf().get("cloud_deployment_id")
                ):
                    try:
                        from common import cloud_client

                        threading.Thread(
                            target=cloud_client.start,
                            args=(self._primary_channel, self),
                            daemon=True,
                        ).start()
                    except Exception:
                        pass

            web_entry = None
            other_entries = []
            for entry in channels:
                if entry[0] == "web":
                    web_entry = entry
                else:
                    other_entries.append(entry)

            ordered = ([web_entry] if web_entry else []) + other_entries
            for i, (name, ch) in enumerate(ordered):
                if i > 0 and name != "web":
                    time.sleep(0.1)
                t = threading.Thread(target=self._run_channel, args=(name, ch), daemon=True)
                self._threads[name] = t
                t.start()
                logger.debug(f"[ChannelManager] Channel '{name}' started in sub-thread")

    def start_channel_config(self, definition):
        """Start one tenant channel config when the channel needs a managed runtime."""
        channel_type = getattr(definition, "channel_type", "")
        channel_config_id = getattr(definition, "channel_config_id", "")
        if not channel_type or not channel_config_id:
            return

        from cow_platform.services.channel_config_service import ChannelConfigService

        service = ChannelConfigService()
        overrides = service.build_runtime_overrides(definition)
        if channel_type in ("wechatmp", "wechatmp_service"):
            logger.info(
                f"[ChannelManager] Channel config '{channel_config_id}' uses web callback routing; no background runtime needed"
            )
            return
        if channel_type == const.WEIXIN and not str(overrides.get("weixin_token", "") or "").strip():
            logger.info(
                f"[ChannelManager] Weixin config '{channel_config_id}' is waiting for QR login; no runtime started"
            )
            return
        if channel_type == const.FEISHU and str(overrides.get("feishu_event_mode", "websocket")) != "websocket":
            logger.info(
                f"[ChannelManager] Feishu config '{channel_config_id}' uses webhook mode; no websocket runtime needed"
            )
            return

        with self._lock:
            existing = self._channels.get(channel_config_id)
        if existing is not None:
            self.remove_channel_config(channel_config_id)

        if not self._acquire_channel_runtime_lease(definition):
            return

        logger.info(f"[ChannelManager] Starting tenant channel config '{channel_config_id}' ({channel_type})")
        _clear_singleton_cache(channel_type)
        from cow_platform.runtime.scope import activate_config_overrides

        try:
            with activate_config_overrides(overrides):
                ch = channel_factory.create_channel(channel_type, singleton_key=channel_config_id)
            ch.cloud_mode = self.cloud_mode
            ch.channel_config_id = channel_config_id
            ch.tenant_id = getattr(definition, "tenant_id", "")
            ch.config_overrides = overrides

            with self._lock:
                self._channels[channel_config_id] = ch
            t = threading.Thread(target=self._run_channel, args=(channel_config_id, ch), daemon=True)
            with self._lock:
                self._threads[channel_config_id] = t
            t.start()
            self._start_channel_runtime_heartbeat(channel_config_id)
            logger.debug(f"[ChannelManager] Tenant channel config '{channel_config_id}' started in sub-thread")
        except Exception:
            self._stop_channel_runtime_lease(channel_config_id, release=True)
            raise

    def start_channel_configs(self, definitions: list):
        for definition in definitions:
            try:
                self.start_channel_config(definition)
            except Exception as e:
                logger.error(
                    f"[ChannelManager] Failed to start channel config '{getattr(definition, 'channel_config_id', '')}': {e}"
                )
                logger.exception(e)

    def sync_channel_configs(self, definitions: list):
        desired = {
            getattr(definition, "channel_config_id", ""): definition
            for definition in definitions
            if getattr(definition, "channel_config_id", "")
        }
        running = set(self.list_channel_config_ids())
        for channel_config_id in sorted(running - set(desired)):
            logger.info(f"[ChannelManager] Stopping stale tenant channel config '{channel_config_id}'")
            self.remove_channel_config(channel_config_id)
        for channel_config_id, definition in desired.items():
            if self.get_channel_config(channel_config_id) is not None:
                continue
            try:
                self.start_channel_config(definition)
            except Exception as e:
                logger.error(f"[ChannelManager] Failed to sync channel config '{channel_config_id}': {e}")
                logger.exception(e)

    def remove_channel_config(self, channel_config_id: str):
        self.stop(channel_config_id)

    def _run_channel(self, name: str, channel):
        try:
            from cow_platform.runtime.scope import activate_config_overrides

            with activate_config_overrides(getattr(channel, "config_overrides", {}) or {}):
                channel.startup()
        except Exception as e:
            logger.error(f"[ChannelManager] Channel '{name}' startup error: {e}")
            logger.exception(e)
        finally:
            channel_config_id = getattr(channel, "channel_config_id", "") or ""
            if channel_config_id:
                self._stop_channel_runtime_lease(channel_config_id, release=True)

    def stop(self, channel_name: str = None):
        """
        Stop one channel, or all channels when no name is provided.
        """
        with self._lock:
            names = [channel_name] if channel_name else list(self._channels.keys())
            to_stop = []
            for name in names:
                ch = self._channels.pop(name, None)
                th = self._threads.pop(name, None)
                to_stop.append((name, ch, th))
            if channel_name and self._primary_channel is self._channels.get(channel_name):
                self._primary_channel = None

        for name, ch, th in to_stop:
            if ch is None:
                logger.warning(f"[ChannelManager] Channel '{name}' not found in managed channels")
                if th and th.is_alive():
                    self._interrupt_thread(th, name)
                continue
            logger.info(f"[ChannelManager] Stopping channel '{name}'...")
            graceful = False
            if hasattr(ch, "stop"):
                try:
                    ch.stop()
                    graceful = True
                except Exception as e:
                    logger.warning(f"[ChannelManager] Error during channel '{name}' stop: {e}")
            if th and th.is_alive():
                th.join(timeout=5)
                if th.is_alive():
                    if graceful:
                        logger.info(
                            f"[ChannelManager] Channel '{name}' thread still alive after stop(), "
                            "leaving daemon thread to finish on its own"
                        )
                    else:
                        logger.warning(f"[ChannelManager] Channel '{name}' thread did not exit in 5s, forcing interrupt")
                        self._interrupt_thread(th, name)
            channel_config_id = getattr(ch, "channel_config_id", "") or ""
            if channel_config_id:
                still_alive = bool(th and th.is_alive())
                self._stop_channel_runtime_lease(channel_config_id, release=not still_alive)

    def _acquire_channel_runtime_lease(self, definition) -> bool:
        channel_config_id = getattr(definition, "channel_config_id", "")
        try:
            lease = self._runtime_leases.acquire(definition)
        except Exception as e:
            logger.error(f"[ChannelManager] Failed to acquire runtime lease for '{channel_config_id}': {e}")
            return False
        if not lease.acquired:
            logger.warning(
                f"[ChannelManager] Skip channel config '{channel_config_id}', runtime lease is owned by another instance"
            )
            return False
        logger.info(
            f"[ChannelManager] Acquired runtime lease for channel config '{channel_config_id}' "
            f"until {lease.lease_until}"
        )
        return True

    def _start_channel_runtime_heartbeat(self, channel_config_id: str):
        stop_event = threading.Event()
        with self._lock:
            old_event = self._lease_stop_events.pop(channel_config_id, None)
            self._lease_stop_events[channel_config_id] = stop_event
        if old_event:
            old_event.set()

        interval = max(5, int(getattr(self._runtime_leases, "ttl_seconds", 90)) // 3)

        def heartbeat_loop():
            failures = 0
            while not stop_event.wait(interval):
                try:
                    if self._runtime_leases.heartbeat(channel_config_id):
                        failures = 0
                        continue
                    logger.error(f"[ChannelManager] Lost runtime lease for channel config '{channel_config_id}'")
                    self.remove_channel_config(channel_config_id)
                    return
                except Exception as e:
                    failures += 1
                    logger.warning(
                        f"[ChannelManager] Runtime lease heartbeat failed for '{channel_config_id}' "
                        f"({failures}/3): {e}"
                    )
                    if failures >= 3:
                        self.remove_channel_config(channel_config_id)
                        return

        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        with self._lock:
            self._lease_threads[channel_config_id] = thread
        thread.start()

    def _stop_channel_runtime_lease(self, channel_config_id: str, *, release: bool):
        with self._lock:
            stop_event = self._lease_stop_events.pop(channel_config_id, None)
            self._lease_threads.pop(channel_config_id, None)
        if stop_event:
            stop_event.set()
        if not release:
            logger.warning(
                f"[ChannelManager] Runtime lease for '{channel_config_id}' will expire; channel thread is still alive"
            )
            return
        try:
            self._runtime_leases.release(channel_config_id)
        except Exception as e:
            logger.warning(f"[ChannelManager] Failed to release runtime lease for '{channel_config_id}': {e}")

    @staticmethod
    def _interrupt_thread(th: threading.Thread, name: str):
        """Raise SystemExit in target thread to break blocking loops like start_forever."""
        import ctypes

        try:
            tid = th.ident
            if tid is None:
                return
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_ulong(tid), ctypes.py_object(SystemExit)
            )
            if res == 1:
                logger.info(f"[ChannelManager] Interrupted thread for channel '{name}'")
            elif res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(tid), None)
                logger.warning(f"[ChannelManager] Failed to interrupt thread for channel '{name}'")
        except Exception as e:
            logger.warning(f"[ChannelManager] Thread interrupt error for '{name}': {e}")

    def restart(self, new_channel_name: str):
        logger.info(f"[ChannelManager] Restarting channel to '{new_channel_name}'...")
        self.stop(new_channel_name)
        _clear_singleton_cache(new_channel_name)
        time.sleep(1)
        self.start([new_channel_name], first_start=False)
        logger.info(f"[ChannelManager] Channel restarted to '{new_channel_name}' successfully")

    def add_channel(self, channel_name: str):
        with self._lock:
            if channel_name in self._channels:
                logger.info(f"[ChannelManager] Channel '{channel_name}' already exists, restarting")
        if self._channels.get(channel_name):
            self.restart(channel_name)
            return
        logger.info(f"[ChannelManager] Adding channel '{channel_name}'...")
        _clear_singleton_cache(channel_name)
        self.start([channel_name], first_start=False)
        logger.info(f"[ChannelManager] Channel '{channel_name}' added successfully")

    def remove_channel(self, channel_name: str):
        with self._lock:
            if channel_name not in self._channels:
                logger.warning(f"[ChannelManager] Channel '{channel_name}' not found, nothing to remove")
                return
        logger.info(f"[ChannelManager] Removing channel '{channel_name}'...")
        self.stop(channel_name)
        logger.info(f"[ChannelManager] Channel '{channel_name}' removed successfully")


def _clear_singleton_cache(channel_name: str):
    """Clear the singleton cache for the channel class so updated config is used."""
    cls_map = {
        "web": "channel.web.web_channel.WebChannel",
        "wechatmp": "channel.wechatmp.wechatmp_channel.WechatMPChannel",
        "wechatmp_service": "channel.wechatmp.wechatmp_channel.WechatMPChannel",
        "wechatcom_app": "channel.wechatcom.wechatcomapp_channel.WechatComAppChannel",
        const.FEISHU: "channel.feishu.feishu_channel.FeiShuChanel",
        const.DINGTALK: "channel.dingtalk.dingtalk_channel.DingTalkChanel",
        const.WECOM_BOT: "channel.wecom_bot.wecom_bot_channel.WecomBotChannel",
        const.QQ: "channel.qq.qq_channel.QQChannel",
        const.WEIXIN: "channel.weixin.weixin_channel.WeixinChannel",
        "wx": "channel.weixin.weixin_channel.WeixinChannel",
    }
    module_path = cls_map.get(channel_name)
    if not module_path:
        return
    try:
        parts = module_path.rsplit(".", 1)
        module_name, class_name = parts[0], parts[1]
        import importlib

        module = importlib.import_module(module_name)
        wrapper = getattr(module, class_name, None)
        if wrapper and hasattr(wrapper, "__closure__") and wrapper.__closure__:
            for cell in wrapper.__closure__:
                try:
                    cell_contents = cell.cell_contents
                    if isinstance(cell_contents, dict):
                        cell_contents.clear()
                        logger.debug(f"[ChannelManager] Cleared singleton cache for {class_name}")
                        break
                except ValueError:
                    pass
    except Exception as e:
        logger.warning(f"[ChannelManager] Failed to clear singleton cache: {e}")
