import type { ReactNode } from 'react';

interface WorkspaceProps {
  children: ReactNode;
  className?: string;
  variant?: 'default' | 'console';
}

export function Workspace({ children, className, variant = 'default' }: WorkspaceProps) {
  return (
    <section className={['page-workspace', variant === 'console' ? 'console-page' : '', className].filter(Boolean).join(' ')}>
      {children}
    </section>
  );
}
