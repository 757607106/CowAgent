import type { RuntimeScope } from '../types';

export function buildQuery(params: Record<string, unknown>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    query.set(key, String(value));
  });
  const text = query.toString();
  return text ? `?${text}` : '';
}

export function scopeQuery(scope: RuntimeScope): Record<string, string> {
  if (scope.bindingId) {
    return { tenant_id: scope.tenantId, binding_id: scope.bindingId };
  }
  if (scope.agentId) {
    return { tenant_id: scope.tenantId, agent_id: scope.agentId };
  }
  return scope.tenantId ? { tenant_id: scope.tenantId } : {};
}

export function scopeBody(scope: RuntimeScope): Record<string, string> {
  if (scope.bindingId) {
    return { tenant_id: scope.tenantId, binding_id: scope.bindingId };
  }
  if (scope.agentId) {
    return { tenant_id: scope.tenantId, agent_id: scope.agentId };
  }
  return scope.tenantId ? { tenant_id: scope.tenantId } : {};
}

export async function requestJson<T = any>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    credentials: 'same-origin',
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  });

  const isJson = res.headers.get('content-type')?.includes('application/json');
  let payload: unknown;
  if (isJson) {
    payload = await res.json();
  } else {
    const text = await res.text();
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!res.ok) {
    const message = typeof payload === 'object' && payload && 'message' in payload
      ? String((payload as Record<string, unknown>).message)
      : `请求失败：${res.status}`;
    throw new Error(message);
  }

  if (typeof payload === 'object' && payload && 'status' in payload) {
    const data = payload as Record<string, unknown>;
    if (data.status === 'error') {
      throw new Error(String(data.message || '服务端返回错误'));
    }
  }

  return payload as T;
}
