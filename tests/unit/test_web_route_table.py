from __future__ import annotations

from channel.web.route_table import build_web_routes


def test_web_route_table_is_pairwise_and_contains_core_routes() -> None:
    routes = build_web_routes()
    assert len(routes) % 2 == 0

    pairs = list(zip(routes[0::2], routes[1::2], strict=True))
    route_map = {path: handler for path, handler in pairs}

    assert route_map["/"] == "RootHandler"
    assert route_map["/auth/register"] == "AuthRegisterHandler"
    assert route_map["/chat"] == "ChatHandler"
    assert route_map["/assets/(.*)"] == "AssetsHandler"
    assert route_map["/api/version"] == "VersionHandler"
    assert route_map["/api/platform/agents"] == "PlatformAgentsHandler"
    assert route_map["/api/platform/usage"] == "PlatformUsageHandler"
    assert route_map["/api/platform/costs"] == "PlatformCostsHandler"
