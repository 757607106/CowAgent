import { createContext, useContext } from 'react';
import type { AuthUser, RuntimeScope } from '../types';

export interface RuntimeAgentOption {
  label: string;
  value: string;
}

export const DEFAULT_AGENT_ID = 'default';
export const DEFAULT_AGENT_NAME = '通用 Agent';
export const WORKSPACE_AGENT_VALUE = '__workspace__';

export function displayAgentName(agentId: string, name?: string): string {
  const trimmed = (name || '').trim();
  if (agentId === DEFAULT_AGENT_ID) {
    return trimmed || DEFAULT_AGENT_NAME;
  }
  return trimmed || agentId;
}

export interface RuntimeContextValue {
  tenantId: string;
  authUser: AuthUser | null;
  scope: RuntimeScope;
  setScope: (next: RuntimeScope) => void;
  agentOptions: RuntimeAgentOption[];
  refreshAgentOptions: () => Promise<void>;
  setAgentScope: (nextAgentId?: string) => void;
  logout: () => Promise<void>;
}

export const RuntimeContext = createContext<RuntimeContextValue | null>(null);

export function useRuntimeScope(): RuntimeContextValue {
  const value = useContext(RuntimeContext);
  if (!value) {
    throw new Error('useRuntimeScope 必须在 RuntimeContext.Provider 内使用');
  }
  return value;
}
