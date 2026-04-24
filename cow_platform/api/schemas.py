from __future__ import annotations

from pydantic import BaseModel, Field

from cow_platform.services.agent_service import DEFAULT_TENANT_ID


class AgentCreateRequest(BaseModel):
    tenant_id: str = Field(default=DEFAULT_TENANT_ID)
    agent_id: str | None = None
    name: str
    model: str = ""
    system_prompt: str = ""
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    knowledge_enabled: bool = False
    mcp_servers: dict[str, object] = Field(default_factory=dict)


class AgentUpdateRequest(BaseModel):
    tenant_id: str = Field(default=DEFAULT_TENANT_ID)
    name: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    tools: list[str] | None = None
    skills: list[str] | None = None
    knowledge_enabled: bool | None = None
    mcp_servers: dict[str, object] | None = None


class TenantCreateRequest(BaseModel):
    tenant_id: str = ""
    name: str
    status: str = "active"
    metadata: dict[str, object] = Field(default_factory=dict)


class TenantUpdateRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    metadata: dict[str, object] | None = None


class TenantUserCreateRequest(BaseModel):
    tenant_id: str
    user_id: str = ""
    name: str = ""
    role: str = "member"
    status: str = "active"
    metadata: dict[str, object] = Field(default_factory=dict)


class TenantUserUpdateRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    status: str | None = None
    metadata: dict[str, object] | None = None


class TenantUserIdentityUpsertRequest(BaseModel):
    tenant_id: str
    user_id: str
    channel_type: str
    external_user_id: str
    metadata: dict[str, object] = Field(default_factory=dict)


class TenantRegisterRequest(BaseModel):
    tenant_id: str = ""
    tenant_name: str
    user_id: str = ""
    account: str = ""
    password: str
    user_name: str = ""


class TenantLoginRequest(BaseModel):
    tenant_id: str = ""
    user_id: str = ""
    account: str = ""
    password: str


class BindingCreateRequest(BaseModel):
    tenant_id: str = Field(default=DEFAULT_TENANT_ID)
    binding_id: str = ""
    name: str
    channel_type: str
    agent_id: str
    enabled: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class BindingUpdateRequest(BaseModel):
    tenant_id: str | None = None
    name: str | None = None
    channel_type: str | None = None
    agent_id: str | None = None
    enabled: bool | None = None
    metadata: dict[str, object] | None = None


class PricingUpsertRequest(BaseModel):
    model: str
    input_price_per_million: float = 0.0
    output_price_per_million: float = 0.0
    currency: str = "CNY"


class QuotaUpsertRequest(BaseModel):
    scope_type: str
    tenant_id: str
    agent_id: str = ""
    max_requests_per_day: int = 0
    max_tokens_per_day: int = 0
    enabled: bool = True


class JobCreateRequest(BaseModel):
    job_type: str
    tenant_id: str = Field(default=DEFAULT_TENANT_ID)
    agent_id: str = Field(default="default")
    payload: dict[str, object] = Field(default_factory=dict)
