from __future__ import annotations

from channel.web import web_channel


def test_web_channel_exports_core_handlers() -> None:
    handler_names = [
        "RootHandler",
        "AuthCheckHandler",
        "AuthLoginHandler",
        "AuthLogoutHandler",
        "MessageHandler",
        "UploadHandler",
        "UploadsHandler",
        "FileServeHandler",
        "PollHandler",
        "StreamHandler",
        "ChatHandler",
        "AssetsHandler",
        "VersionHandler",
    ]

    for name in handler_names:
        handler = getattr(web_channel, name, None)
        assert isinstance(handler, type), f"missing handler class: {name}"
