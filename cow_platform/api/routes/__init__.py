from cow_platform.api.routes.auth import register_auth_routes
from cow_platform.api.routes.agent_binding import register_agent_binding_routes
from cow_platform.api.routes.channel_config import register_channel_config_routes
from cow_platform.api.routes.governance import register_governance_routes
from cow_platform.api.routes.platform_admin import register_model_config_routes, register_platform_admin_routes
from cow_platform.api.routes.system import register_system_routes
from cow_platform.api.routes.tenants import register_tenant_routes

__all__ = [
    "register_auth_routes",
    "register_agent_binding_routes",
    "register_channel_config_routes",
    "register_governance_routes",
    "register_model_config_routes",
    "register_platform_admin_routes",
    "register_system_routes",
    "register_tenant_routes",
]
