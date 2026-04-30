from __future__ import annotations

import json

import web

from common.log import logger
from channel.web.handlers.dependencies import (
    _get_agent_service,
    _get_authenticated_tenant_session,
    _get_binding_service,
    _get_channel_config_service,
    _get_model_config_service,
    _get_tenant_service,
    _get_tenant_user_service,
    _get_usage_service,
    _is_tenant_auth_enabled,
    _parse_bool,
    _raise_forbidden,
    _require_auth,
    _require_platform_admin,
    _require_tenant_manage,
    _restart_channel_config_runtime,
    _scope_optional_tenant_id,
    _scope_tenant_id,
    _stop_channel_config_runtime,
)

class AgentsHandler:
    """Simple agent listing API – also enforces tenant isolation via _scope_optional_tenant_id."""

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', channel_type='', channel_config_id='')
            service = _get_agent_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            return json.dumps(
                {"status": "success", "agents": service.list_agent_records(tenant_id or 'default')},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] Agents API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformTenantUserMetaHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from cow_platform.services.tenant_user_service import TenantUserService

            return json.dumps(
                {
                    "status": "success",
                    "roles": list(TenantUserService.list_roles()),
                    "statuses": list(TenantUserService.list_statuses()),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserMeta GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformAdminTenantsHandler:
    def GET(self):
        _require_platform_admin()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_tenant_service()
            return json.dumps({"status": "success", "tenants": service.list_tenant_records()}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAdminTenants GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_platform_admin()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_tenant_service()
            result = service.create_tenant(
                tenant_id=str(body.get("tenant_id", "")).strip(),
                name=str(body.get("name", "")).strip(),
                status=str(body.get("status", "active")).strip() or "active",
                metadata=body.get("metadata", {}),
            )
            _get_agent_service().ensure_default_agent(result["tenant_id"])
            return json.dumps({"status": "success", "tenant": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAdminTenants POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformAdminTenantDetailHandler:
    def PUT(self, tenant_id):
        _require_platform_admin()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            result = _get_tenant_service().update_tenant(
                tenant_id=str(tenant_id).strip(),
                name=body.get("name"),
                status=body.get("status"),
                metadata=body.get("metadata"),
            )
            return json.dumps({"status": "success", "tenant": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAdminTenantDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def DELETE(self, tenant_id):
        _require_platform_admin()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            result = _get_tenant_service().delete_tenant(str(tenant_id).strip())
            return json.dumps({"status": "success", "tenant": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAdminTenantDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformAdminModelsHandler:
    def GET(self):
        _require_platform_admin()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_model_config_service()
            return json.dumps(
                {
                    "status": "success",
                    "providers": service.list_provider_options(scope="platform"),
                    "models": [service.serialize_model(item) for item in service.list_platform_models()],
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAdminModels GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_platform_admin()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            session = _get_authenticated_tenant_session()
            model = _get_model_config_service().create_platform_model(
                provider=str(body.get("provider", "")).strip(),
                model_name=str(body.get("model_name", "")).strip(),
                display_name=str(body.get("display_name", "")).strip(),
                api_key=str(body.get("api_key", "") or ""),
                api_base=str(body.get("api_base", "") or ""),
                enabled=_parse_bool(body.get("enabled"), True),
                is_public=_parse_bool(body.get("is_public"), True),
                metadata=body.get("metadata", {}),
                created_by=session.user_id if session else "",
            )
            return json.dumps({"status": "success", "model": model}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAdminModels POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformAdminModelDetailHandler:
    def PUT(self, model_config_id):
        _require_platform_admin()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            model = _get_model_config_service().update_model(
                str(model_config_id).strip(),
                expected_scope="platform",
                provider=body.get("provider"),
                model_name=body.get("model_name"),
                display_name=body.get("display_name"),
                api_key=body.get("api_key"),
                api_base=body.get("api_base"),
                enabled=body.get("enabled"),
                is_public=body.get("is_public"),
                metadata=body.get("metadata"),
            )
            return json.dumps({"status": "success", "model": model}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAdminModelDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def DELETE(self, model_config_id):
        _require_platform_admin()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            model = _get_model_config_service().delete_model(str(model_config_id).strip(), expected_scope="platform")
            return json.dumps({"status": "success", "model": model}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAdminModelDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformAvailableModelsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='')
            tenant_id = _scope_tenant_id(params.tenant_id)
            service = _get_model_config_service()
            return json.dumps(
                {
                    "status": "success",
                    "models": [service.serialize_model(item) for item in service.list_available_models(tenant_id)],
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAvailableModels GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformTenantModelsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='')
            tenant_id = _scope_tenant_id(params.tenant_id)
            service = _get_model_config_service()
            return json.dumps(
                {
                    "status": "success",
                    "providers": service.list_provider_options(scope="tenant"),
                    "models": [service.serialize_model(item) for item in service.list_tenant_models(tenant_id)],
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantModels GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "")).strip())
            session = _get_authenticated_tenant_session()
            model = _get_model_config_service().create_tenant_model(
                tenant_id=tenant_id,
                provider=str(body.get("provider", "")).strip(),
                model_name=str(body.get("model_name", "")).strip(),
                display_name=str(body.get("display_name", "")).strip(),
                api_key=str(body.get("api_key", "") or ""),
                api_base=str(body.get("api_base", "") or ""),
                enabled=_parse_bool(body.get("enabled"), True),
                metadata=body.get("metadata", {}),
                created_by=session.user_id if session else "",
            )
            return json.dumps({"status": "success", "model": model}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantModels POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformTenantModelDetailHandler:
    def PUT(self, model_config_id):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            session = _get_authenticated_tenant_session()
            model = _get_model_config_service().update_model(
                str(model_config_id).strip(),
                expected_scope="tenant",
                tenant_id=session.tenant_id if session else "",
                provider=body.get("provider"),
                model_name=body.get("model_name"),
                display_name=body.get("display_name"),
                api_key=body.get("api_key"),
                api_base=body.get("api_base"),
                enabled=body.get("enabled"),
                is_public=False,
                metadata=body.get("metadata"),
            )
            return json.dumps({"status": "success", "model": model}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantModelDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def DELETE(self, model_config_id):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            session = _get_authenticated_tenant_session()
            model = _get_model_config_service().delete_model(
                str(model_config_id).strip(),
                expected_scope="tenant",
                tenant_id=session.tenant_id if session else "",
            )
            return json.dumps({"status": "success", "model": model}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantModelDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformTenantsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_tenant_service()
            session = _get_authenticated_tenant_session()
            if session and session.principal_type == "platform":
                _raise_forbidden("请使用平台租户管理入口")
            if session and session.principal_type == "tenant":
                definition = service.resolve_tenant(session.tenant_id)
                tenants = [service.serialize_tenant(definition)]
            else:
                tenants = service.list_tenant_records()
            return json.dumps(
                {"status": "success", "tenants": tenants},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenants GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        if _is_tenant_auth_enabled():
            _require_platform_admin()
        else:
            _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_tenant_service()
            result = service.create_tenant(
                tenant_id=_scope_tenant_id(str(body.get("tenant_id", "")).strip()),
                name=str(body.get("name", "")).strip(),
                status=str(body.get("status", "active")).strip() or "active",
                metadata=body.get("metadata", {}),
            )
            _get_agent_service().ensure_default_agent(result["tenant_id"])
            return json.dumps({"status": "success", "tenant": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenants POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformTenantDetailHandler:
    def GET(self, tenant_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_tenant_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            definition = service.resolve_tenant(scoped_tenant_id)
            return json.dumps(
                {"status": "success", "tenant": service.serialize_tenant(definition)},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantDetail GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def PUT(self, tenant_id):
        if _is_tenant_auth_enabled():
            _require_platform_admin()
        else:
            _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_tenant_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            result = service.update_tenant(
                tenant_id=scoped_tenant_id,
                name=body.get("name"),
                status=body.get("status"),
                metadata=body.get("metadata"),
            )
            return json.dumps({"status": "success", "tenant": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformTenantUsersHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', role='', status='')
            service = _get_tenant_user_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            return json.dumps(
                {
                    "status": "success",
                    "tenant_users": service.list_user_records(
                        tenant_id=tenant_id,
                        role=(params.role or "").strip(),
                        status=(params.status or "").strip(),
                    ),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUsers GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_tenant_user_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "")).strip())
            result = service.create_user(
                tenant_id=tenant_id,
                user_id=str(body.get("user_id", "")).strip(),
                account=str(body.get("account", "")).strip(),
                name=str(body.get("name", "")).strip(),
                role=str(body.get("role", "member")).strip() or "member",
                status=str(body.get("status", "active")).strip() or "active",
                password=str(body.get("password", "")).strip(),
                metadata=body.get("metadata", {}),
            )
            return json.dumps({"status": "success", "tenant_user": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUsers POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformTenantUserDetailHandler:
    def GET(self, tenant_id, user_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_tenant_user_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            definition = service.resolve_user(tenant_id=scoped_tenant_id, user_id=str(user_id).strip())
            return json.dumps(
                {"status": "success", "tenant_user": service.serialize_user(definition)},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserDetail GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def PUT(self, tenant_id, user_id):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_tenant_user_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            result = service.update_user(
                tenant_id=scoped_tenant_id,
                user_id=str(user_id).strip(),
                name=body.get("name"),
                role=body.get("role"),
                status=body.get("status"),
                metadata=body.get("metadata"),
            )
            return json.dumps({"status": "success", "tenant_user": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def DELETE(self, tenant_id, user_id):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_tenant_user_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            result = service.delete_user(
                tenant_id=scoped_tenant_id,
                user_id=str(user_id).strip(),
            )
            return json.dumps({"status": "success", "tenant_user": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformTenantUserIdentitiesHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', user_id='', channel_type='')
            service = _get_tenant_user_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            return json.dumps(
                {
                    "status": "success",
                    "identities": service.list_identity_records(
                        tenant_id=tenant_id,
                        user_id=(params.user_id or "").strip(),
                        channel_type=(params.channel_type or "").strip(),
                    ),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserIdentities GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_tenant_user_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "")).strip())
            result = service.bind_identity(
                tenant_id=tenant_id,
                user_id=str(body.get("user_id", "")).strip(),
                channel_type=str(body.get("channel_type", "")).strip(),
                external_user_id=str(body.get("external_user_id", "")).strip(),
                metadata=body.get("metadata", {}),
            )
            return json.dumps({"status": "success", "identity": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserIdentities POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformTenantUserIdentityDetailHandler:
    def DELETE(self, tenant_id, channel_type, external_user_id):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_tenant_user_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            result = service.unbind_identity(
                tenant_id=scoped_tenant_id,
                channel_type=str(channel_type).strip(),
                external_user_id=str(external_user_id).strip(),
            )
            return json.dumps({"status": "success", "identity": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserIdentityDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformChannelConfigsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', channel_type='', channel_config_id='')
            service = _get_channel_config_service()
            tenant_id = _scope_tenant_id(params.tenant_id)
            return json.dumps(
                {
                    "status": "success",
                    "channel_types": service.list_channel_type_defs(),
                    "channel_configs": [
                        service.serialize_channel_config(item)
                        for item in service.list_channel_configs(
                            tenant_id=tenant_id,
                            channel_type=(params.channel_type or "").strip(),
                        )
                    ],
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformChannelConfigs GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_channel_config_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "default")).strip())
            result = service.create_channel_config(
                tenant_id=tenant_id,
                channel_config_id=str(body.get("channel_config_id", "") or ""),
                name=str(body.get("name", "") or ""),
                channel_type=str(body.get("channel_type", "") or ""),
                config=body.get("config", {}) or {},
                enabled=bool(body.get("enabled", True)),
                metadata=body.get("metadata", {}) or {},
                created_by=(_get_authenticated_tenant_session().user_id if _get_authenticated_tenant_session() else ""),
            )
            _restart_channel_config_runtime(result["channel_config_id"])
            return json.dumps({"status": "success", "channel_config": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformChannelConfigs POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformChannelConfigDetailHandler:
    def GET(self, channel_config_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='')
            service = _get_channel_config_service()
            tenant_id = _scope_tenant_id(params.tenant_id)
            definition = service.resolve_channel_config(
                tenant_id=tenant_id,
                channel_config_id=str(channel_config_id).strip(),
            )
            return json.dumps(
                {"status": "success", "channel_config": service.serialize_channel_config(definition)},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformChannelConfigDetail GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def PUT(self, channel_config_id):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_channel_config_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "") or ""))
            result = service.update_channel_config(
                channel_config_id=str(channel_config_id).strip(),
                tenant_id=tenant_id,
                name=body.get("name"),
                channel_type=body.get("channel_type"),
                config=body.get("config"),
                enabled=body.get("enabled"),
                metadata=body.get("metadata"),
            )
            _restart_channel_config_runtime(result["channel_config_id"])
            return json.dumps({"status": "success", "channel_config": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformChannelConfigDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def DELETE(self, channel_config_id):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='')
            service = _get_channel_config_service()
            tenant_id = _scope_tenant_id(params.tenant_id)
            result = service.delete_channel_config(
                channel_config_id=str(channel_config_id).strip(),
                tenant_id=tenant_id,
            )
            _stop_channel_config_runtime(result["channel_config_id"])
            return json.dumps({"status": "success", "channel_config": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformChannelConfigDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformAgentsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='default')
            service = _get_agent_service()
            tenant_id = _scope_tenant_id(params.tenant_id)
            return json.dumps(
                {"status": "success", "agents": service.list_agent_records(tenant_id)},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAgents GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_agent_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "default")).strip())
            result = service.create_agent(
                tenant_id=tenant_id,
                agent_id=(body.get("agent_id") or None),
                name=str(body.get("name", "")),
                model=str(body.get("model", "")),
                model_config_id=str(body.get("model_config_id", "") or ""),
                system_prompt=str(body.get("system_prompt", "")),
                metadata=body.get("metadata", {}),
                tools=body.get("tools", []),
                skills=body.get("skills", []),
                knowledge_enabled=bool(body.get("knowledge_enabled", False)),
                mcp_servers=body.get("mcp_servers", {}),
            )
            return json.dumps({"status": "success", "agent": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAgents POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformAgentDetailHandler:
    def GET(self, agent_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='default')
            tenant_id = _scope_tenant_id(params.tenant_id)
            service = _get_agent_service()
            definition = service.resolve_agent(tenant_id=tenant_id, agent_id=agent_id)
            return json.dumps(
                {"status": "success", "agent": service.serialize_agent(definition)},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAgentDetail GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def PUT(self, agent_id):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_agent_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "default")).strip())
            result = service.update_agent(
                agent_id=agent_id,
                tenant_id=tenant_id,
                name=body.get("name"),
                model=body.get("model"),
                model_config_id=body.get("model_config_id"),
                system_prompt=body.get("system_prompt"),
                metadata=body.get("metadata"),
                tools=body.get("tools"),
                skills=body.get("skills"),
                knowledge_enabled=body.get("knowledge_enabled"),
                mcp_servers=body.get("mcp_servers"),
            )
            return json.dumps({"status": "success", "agent": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAgentDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def DELETE(self, agent_id):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='default')
            tenant_id = _scope_tenant_id(params.tenant_id)
            service = _get_agent_service()
            deleted = service.delete_agent(agent_id=agent_id, tenant_id=tenant_id)
            return json.dumps(
                {"status": "success", "agent": deleted, "agent_id": agent_id},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAgentDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class BindingsHandler:
    """Simple binding listing API – also enforces tenant isolation via _scope_optional_tenant_id."""

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', channel_type='', channel_config_id='')
            service = _get_binding_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            return json.dumps(
                {
                    "status": "success",
                    "bindings": service.list_binding_records(
                        tenant_id=tenant_id,
                        channel_type=(params.channel_type or "").strip(),
                        channel_config_id=(params.channel_config_id or "").strip(),
                    ),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] Bindings API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformBindingsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', channel_type='', channel_config_id='')
            service = _get_binding_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            return json.dumps(
                {
                    "status": "success",
                    "bindings": service.list_binding_records(
                        tenant_id=tenant_id,
                        channel_type=(params.channel_type or "").strip(),
                        channel_config_id=(params.channel_config_id or "").strip(),
                    ),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformBindings GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_binding_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "default")).strip())
            result = service.create_binding(
                tenant_id=tenant_id,
                binding_id=str(body.get("binding_id", "")),
                name=str(body.get("name", "")),
                channel_type=str(body.get("channel_type", "")),
                channel_config_id=str(body.get("channel_config_id", "") or ""),
                agent_id=str(body.get("agent_id", "")),
                enabled=bool(body.get("enabled", True)),
                metadata=body.get("metadata", {}),
            )
            return json.dumps({"status": "success", "binding": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformBindings POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformBindingDetailHandler:
    def GET(self, binding_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='')
            service = _get_binding_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            definition = service.resolve_binding(binding_id=binding_id, tenant_id=tenant_id)
            return json.dumps(
                {"status": "success", "binding": service.serialize_binding(definition)},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformBindingDetail GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def PUT(self, binding_id):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_binding_service()
            tenant_id = _scope_optional_tenant_id(body.get("tenant_id", "") or "")
            result = service.update_binding(
                binding_id=binding_id,
                tenant_id=tenant_id,
                name=body.get("name"),
                channel_type=body.get("channel_type"),
                channel_config_id=body.get("channel_config_id"),
                agent_id=body.get("agent_id"),
                enabled=body.get("enabled"),
                metadata=body.get("metadata"),
            )
            return json.dumps({"status": "success", "binding": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformBindingDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def DELETE(self, binding_id):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='')
            service = _get_binding_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            result = service.delete_binding(binding_id=binding_id, tenant_id=tenant_id)
            return json.dumps({"status": "success", "binding": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformBindingDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformUsageHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', agent_id='', bucket='', day='', start='', end='', model='', request_id='', limit='100')
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            usage = _get_usage_service().list_usage_records(
                tenant_id=tenant_id,
                agent_id=(params.agent_id or "").strip(),
                bucket=(params.bucket or "").strip(),
                day=(params.day or "").strip(),
                start=(params.start or "").strip(),
                end=(params.end or "").strip(),
                model=(params.model or "").strip(),
                request_id=(params.request_id or "").strip(),
                limit=int(params.limit or 100),
            )
            return json.dumps({"status": "success", "usage": usage}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformUsage GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformUsageAnalyticsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', agent_id='', bucket='day', start='', end='', model='', limit='10')
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            analytics = _get_usage_service().get_usage_analytics(
                tenant_id=tenant_id,
                agent_id=(params.agent_id or "").strip(),
                bucket=(params.bucket or "day").strip(),
                start=(params.start or "").strip(),
                end=(params.end or "").strip(),
                model=(params.model or "").strip(),
                limit=int(params.limit or 10),
            )
            return json.dumps({"status": "success", "analytics": analytics}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformUsageAnalytics GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class PlatformCostsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', agent_id='', day='', start='', end='', model='')
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            summary = _get_usage_service().summarize_usage(
                tenant_id=tenant_id,
                agent_id=(params.agent_id or "").strip(),
                day=(params.day or "").strip(),
                start=(params.start or "").strip(),
                end=(params.end or "").strip(),
                model=(params.model or "").strip(),
            )
            return json.dumps({"status": "success", "summary": summary}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformCosts GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


__all__ = ["AgentsHandler", "PlatformTenantUserMetaHandler", "PlatformAdminTenantsHandler", "PlatformAdminTenantDetailHandler", "PlatformAdminModelsHandler", "PlatformAdminModelDetailHandler", "PlatformAvailableModelsHandler", "PlatformTenantModelsHandler", "PlatformTenantModelDetailHandler", "PlatformTenantsHandler", "PlatformTenantDetailHandler", "PlatformTenantUsersHandler", "PlatformTenantUserDetailHandler", "PlatformTenantUserIdentitiesHandler", "PlatformTenantUserIdentityDetailHandler", "PlatformChannelConfigsHandler", "PlatformChannelConfigDetailHandler", "PlatformAgentsHandler", "PlatformAgentDetailHandler", "BindingsHandler", "PlatformBindingsHandler", "PlatformBindingDetailHandler", "PlatformUsageHandler", "PlatformUsageAnalyticsHandler", "PlatformCostsHandler"]
