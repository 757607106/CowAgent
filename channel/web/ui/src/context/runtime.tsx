import { createContext, useContext } from 'react';
import type { RuntimeScope } from '../types';

export interface RuntimeContextValue {
  scope: RuntimeScope;
  setScope: (next: RuntimeScope) => void;
}

export const RuntimeContext = createContext<RuntimeContextValue | null>(null);

export function useRuntimeScope(): RuntimeContextValue {
  const value = useContext(RuntimeContext);
  if (!value) {
    throw new Error('useRuntimeScope 必须在 RuntimeContext.Provider 内使用');
  }
  return value;
}
