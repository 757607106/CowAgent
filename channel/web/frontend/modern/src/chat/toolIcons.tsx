import type { CSSProperties, ReactNode } from 'react';
import type { AssistantStep } from '../types';

type ToolIconKey =
  | 'read'
  | 'write'
  | 'edit'
  | 'ls'
  | 'bash'
  | 'vision'
  | 'send'
  | 'web_fetch'
  | 'browser'
  | 'memory_search'
  | 'memory_get'
  | 'scheduler'
  | 'env_config';

type ToolIconStatus = AssistantStep['status'];

interface ToolIconDefinition {
  Icon: () => ReactNode;
  color: string;
  bg: string;
  border: string;
}

const lineProps = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
} as const;

function ToolSvg({ children }: { children: ReactNode }) {
  return (
    <svg
      className="chat-tool-step-icon-svg"
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

function ReadIcon() {
  return (
    <ToolSvg>
      <path {...lineProps} d="M6.25 3.75h7.25L18 8.25v12H6.25z" />
      <path {...lineProps} d="M13.5 3.75v4.5H18" />
      <path {...lineProps} d="M8.75 11h4.5" />
      <circle {...lineProps} cx="13.9" cy="15.1" r="2.15" />
      <path {...lineProps} d="m15.55 16.75 2.25 2.25" />
    </ToolSvg>
  );
}

function WriteIcon() {
  return (
    <ToolSvg>
      <path {...lineProps} d="M6.25 3.75h7.25L18 8.25v12H6.25z" />
      <path {...lineProps} d="M13.5 3.75v4.5H18" />
      <path {...lineProps} d="M12.1 12.25v5" />
      <path {...lineProps} d="M9.6 14.75h5" />
    </ToolSvg>
  );
}

function EditIcon() {
  return (
    <ToolSvg>
      <path {...lineProps} d="M5 5.5h8.25" />
      <path {...lineProps} d="M5 18.75h14V10.5" />
      <path {...lineProps} d="m11.25 15.85.7-2.8 5.55-5.55 2 2-5.55 5.55z" />
      <path {...lineProps} d="m16.45 8.55 2 2" />
    </ToolSvg>
  );
}

function LsIcon() {
  return (
    <ToolSvg>
      <path {...lineProps} d="M3.75 7.75h6.1l1.65 2h8.75v7.7a2 2 0 0 1-2 2H5.75a2 2 0 0 1-2-2z" />
      <path {...lineProps} d="M3.75 7.75V6.6a2 2 0 0 1 2-2h3.2l1.75 2.05h7.55a2 2 0 0 1 2 2v1.1" />
    </ToolSvg>
  );
}

function BashIcon() {
  return (
    <ToolSvg>
      <rect {...lineProps} x="3.75" y="4.75" width="16.5" height="14.5" rx="3" />
      <path {...lineProps} d="m7.25 9.25 3 3-3 3" />
      <path {...lineProps} d="M12.75 15.25h4" />
    </ToolSvg>
  );
}

function VisionIcon() {
  return (
    <ToolSvg>
      <rect {...lineProps} x="4.25" y="5.25" width="15.5" height="13.5" rx="3" />
      <path {...lineProps} d="m7.2 15.5 3-3 2.35 2.35 1.7-1.7 2.55 2.55" />
      <circle cx="9" cy="9.35" r="1.05" fill="currentColor" />
      <path {...lineProps} d="M17.4 3.5v2.15" />
      <path {...lineProps} d="M16.3 4.6h2.2" />
    </ToolSvg>
  );
}

function SendIcon() {
  return (
    <ToolSvg>
      <path {...lineProps} d="M4 11.7 20 4.75l-6.45 14.5-3.05-5.8z" />
      <path {...lineProps} d="m10.5 13.45 4.45-4.35" />
    </ToolSvg>
  );
}

function WebFetchIcon() {
  return (
    <ToolSvg>
      <circle {...lineProps} cx="12" cy="12" r="8.25" />
      <path {...lineProps} d="M4 12h16" />
      <path {...lineProps} d="M12 3.75c2.15 2.25 3.2 5 3.2 8.25s-1.05 6-3.2 8.25" />
      <path {...lineProps} d="M12 3.75C9.85 6 8.8 8.75 8.8 12s1.05 6 3.2 8.25" />
      <path {...lineProps} d="m15.1 15.15 2 2 2-2" />
    </ToolSvg>
  );
}

function BrowserIcon() {
  return (
    <ToolSvg>
      <rect {...lineProps} x="3.75" y="5" width="16.5" height="14" rx="3" />
      <path {...lineProps} d="M3.75 9.25h16.5" />
      <path {...lineProps} d="M7 7.15h.01" />
      <path {...lineProps} d="M10 7.15h.01" />
      <path {...lineProps} d="m13.25 12.15 4.5 2-2.05.85-.85 2.05z" />
    </ToolSvg>
  );
}

function MemorySearchIcon() {
  return (
    <ToolSvg>
      <ellipse {...lineProps} cx="10.4" cy="6.5" rx="5.6" ry="2.55" />
      <path {...lineProps} d="M4.8 6.5v6.35c0 1.4 2.05 2.55 5.6 2.55.8 0 1.52-.06 2.15-.18" />
      <path {...lineProps} d="M16 6.5v5.1" />
      <path {...lineProps} d="M5.1 10c.9 1 2.65 1.55 5.3 1.55 1.2 0 2.22-.12 3.05-.38" />
      <circle {...lineProps} cx="15.55" cy="15.65" r="2.25" />
      <path {...lineProps} d="m17.2 17.3 2.25 2.25" />
    </ToolSvg>
  );
}

function MemoryGetIcon() {
  return (
    <ToolSvg>
      <ellipse {...lineProps} cx="12" cy="6.5" rx="6.5" ry="2.55" />
      <path {...lineProps} d="M5.5 6.5v8.2c0 1.42 2.35 2.58 6.5 2.58s6.5-1.16 6.5-2.58V6.5" />
      <path {...lineProps} d="M5.75 10.3c1.05 1 3.05 1.55 6.25 1.55s5.2-.55 6.25-1.55" />
      <path {...lineProps} d="M5.75 14c1.05 1 3.05 1.55 6.25 1.55s5.2-.55 6.25-1.55" />
      <path {...lineProps} d="m12 19.1 2.25-2.25" />
    </ToolSvg>
  );
}

function SchedulerIcon() {
  return (
    <ToolSvg>
      <rect {...lineProps} x="4.25" y="5.25" width="15.5" height="14.25" rx="3" />
      <path {...lineProps} d="M8.1 3.75v3" />
      <path {...lineProps} d="M15.9 3.75v3" />
      <path {...lineProps} d="M4.25 9.2h15.5" />
      <circle {...lineProps} cx="15.1" cy="15.15" r="2.65" />
      <path {...lineProps} d="M15.1 13.65v1.65l1.25.75" />
    </ToolSvg>
  );
}

function EnvConfigIcon() {
  return (
    <ToolSvg>
      <path {...lineProps} d="M5 7.25h4" />
      <path {...lineProps} d="M14.75 7.25H19" />
      <circle {...lineProps} cx="11.75" cy="7.25" r="2.1" />
      <path {...lineProps} d="M5 12h8.25" />
      <path {...lineProps} d="M17.5 12H19" />
      <circle {...lineProps} cx="15.35" cy="12" r="2.1" />
      <path {...lineProps} d="M5 16.75h2.25" />
      <path {...lineProps} d="M12 16.75h7" />
      <circle {...lineProps} cx="9.35" cy="16.75" r="2.1" />
    </ToolSvg>
  );
}

function GenericToolIcon() {
  return (
    <ToolSvg>
      <path {...lineProps} d="M9.2 4.8 5.35 8.65l3.35 3.35-3.35 3.35 3.85 3.85" />
      <path {...lineProps} d="M14.8 4.8 18.65 8.65 15.3 12l3.35 3.35-3.85 3.85" />
    </ToolSvg>
  );
}

function ReasoningIcon() {
  return (
    <svg
      className="chat-tool-step-icon-svg"
      viewBox="0 0 500 480"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="m495.300012,240.049988c0,-32.5 -40.7,-63.3 -103.1,-82.4c14.4,-63.6 8,-114.2 -20.2,-130.4c-6.5,-3.8 -14.1,-5.6 -22.4,-5.6l0,22.3c4.6,0 8.3,0.9 11.4,2.6c13.6,7.8 19.5,37.5 14.9,75.7c-1.1,9.4 -2.9,19.3 -5.1,29.4c-19.6,-4.8 -41,-8.5 -63.5,-10.9c-13.5,-18.5 -27.5,-35.3 -41.6,-50c32.6,-30.3 63.2,-46.9 84,-46.9l0,-22.3c0,0 0,0 0,0c-27.5,0 -63.5,19.6 -99.9,53.6c-36.4,-33.8 -72.4,-53.2 -99.9,-53.2l0,22.3c20.7,0 51.4,16.5 84,46.6c-14,14.7 -28,31.4 -41.3,49.9c-22.6,2.4 -44,6.1 -63.6,11c-2.3,-10 -4,-19.7 -5.2,-29c-4.7,-38.2 1.1,-67.9 14.6,-75.8c3,-1.8 6.9,-2.6 11.5,-2.6l0,-22.3c0,0 0,0 0,0c-8.4,0 -16,1.8 -22.6,5.6c-28.1,16.2 -34.4,66.7 -19.9,130.1c-62.2,19.2 -102.7,49.9 -102.7,82.3c0,32.5 40.7,63.3 103.1,82.4c-14.4,63.6 -8,114.2 20.2,130.4c6.5,3.8 14.1,5.6 22.5,5.6c27.5,0 63.5,-19.6 99.9,-53.6c36.4,33.8 72.4,53.2 99.9,53.2c8.4,0 16,-1.8 22.6,-5.6c28.1,-16.2 34.4,-66.7 19.9,-130.1c62,-19.1 102.5,-49.9 102.5,-82.3zm-130.2,-66.7c-3.7,12.9 -8.3,26.2 -13.5,39.5c-4.1,-8 -8.4,-16 -13.1,-24c-4.6,-8 -9.5,-15.8 -14.4,-23.4c14.2,2.1 27.9,4.7 41,7.9zm-45.8,106.5c-7.8,13.5 -15.8,26.3 -24.1,38.2c-14.9,1.3 -30,2 -45.2,2c-15.1,0 -30.2,-0.7 -45,-1.9c-8.3,-11.9 -16.4,-24.6 -24.2,-38c-7.6,-13.1 -14.5,-26.4 -20.8,-39.8c6.2,-13.4 13.2,-26.8 20.7,-39.9c7.8,-13.5 15.8,-26.3 24.1,-38.2c14.9,-1.3 30,-2 45.2,-2c15.1,0 30.2,0.7 45,1.9c8.3,11.9 16.4,24.6 24.2,38c7.6,13.1 14.5,26.4 20.8,39.8c-6.3,13.4 -13.2,26.8 -20.7,39.9zm32.3,-13c5.4,13.4 10,26.8 13.8,39.8c-13.1,3.2 -26.9,5.9 -41.2,8c4.9,-7.7 9.8,-15.6 14.4,-23.7c4.6,-8 8.9,-16.1 13,-24.1zm-101.4,106.7c-9.3,-9.6 -18.6,-20.3 -27.8,-32c9,0.4 18.2,0.7 27.5,0.7c9.4,0 18.7,-0.2 27.8,-0.7c-9,11.7 -18.3,22.4 -27.5,32zm-74.4,-58.9c-14.2,-2.1 -27.9,-4.7 -41,-7.9c3.7,-12.9 8.3,-26.2 13.5,-39.5c4.1,8 8.4,16 13.1,24c4.7,8 9.5,15.8 14.4,23.4zm73.9,-208.1c9.3,9.6 18.6,20.3 27.8,32c-9,-0.4 -18.2,-0.7 -27.5,-0.7c-9.4,0 -18.7,0.2 -27.8,0.7c9,-11.7 18.3,-22.4 27.5,-32zm-74,58.9c-4.9,7.7 -9.8,15.6 -14.4,23.7c-4.6,8 -8.9,16 -13,24c-5.4,-13.4 -10,-26.8 -13.8,-39.8c13.1,-3.1 26.9,-5.8 41.2,-7.9zm-90.5,125.2c-35.4,-15.1 -58.3,-34.9 -58.3,-50.6c0,-15.7 22.9,-35.6 58.3,-50.6c8.6,-3.7 18,-7 27.7,-10.1c5.7,19.6 13.2,40 22.5,60.9c-9.2,20.8 -16.6,41.1 -22.2,60.6c-9.9,-3.1 -19.3,-6.5 -28,-10.2zm53.8,142.9c-13.6,-7.8 -19.5,-37.5 -14.9,-75.7c1.1,-9.4 2.9,-19.3 5.1,-29.4c19.6,4.8 41,8.5 63.5,10.9c13.5,18.5 27.5,35.3 41.6,50c-32.6,30.3 -63.2,46.9 -84,46.9c-4.5,-0.1 -8.3,-1 -11.3,-2.7zm237.2,-76.2c4.7,38.2 -1.1,67.9 -14.6,75.8c-3,1.8 -6.9,2.6 -11.5,2.6c-20.7,0 -51.4,-16.5 -84,-46.6c14,-14.7 28,-31.4 41.3,-49.9c22.6,-2.4 44,-6.1 63.6,-11c2.3,10.1 4.1,19.8 5.2,29.1zm38.5,-66.7c-8.6,3.7 -18,7 -27.7,10.1c-5.7,-19.6 -13.2,-40 -22.5,-60.9c9.2,-20.8 16.6,-41.1 22.2,-60.6c9.9,3.1 19.3,6.5 28.1,10.2c35.4,15.1 58.3,34.9 58.3,50.6c-0.1,15.7 -23,35.6 -58.4,50.6z"
        fill="currentColor"
      />
      <circle r="45.700001" cy="240.049988" cx="249.900012" fill="currentColor" />
    </svg>
  );
}

const toolIconDefinitions: Record<ToolIconKey, ToolIconDefinition> = {
  read: { Icon: ReadIcon, color: '#2151D1', bg: '#EEF3FF', border: '#D8E4FF' },
  write: { Icon: WriteIcon, color: '#0F8A5F', bg: '#EAF8F1', border: '#CBEFDF' },
  edit: { Icon: EditIcon, color: '#7C3AED', bg: '#F2ECFF', border: '#DED0FF' },
  ls: { Icon: LsIcon, color: '#B76E00', bg: '#FFF5E3', border: '#F5D49B' },
  bash: { Icon: BashIcon, color: '#273142', bg: '#EEF1F5', border: '#DCE2EA' },
  vision: { Icon: VisionIcon, color: '#8B45D9', bg: '#F4EDFF', border: '#E4D4FF' },
  send: { Icon: SendIcon, color: '#0B74DE', bg: '#EAF4FF', border: '#CFE7FF' },
  web_fetch: { Icon: WebFetchIcon, color: '#0B7F83', bg: '#E7F6F6', border: '#C8EAEA' },
  browser: { Icon: BrowserIcon, color: '#334155', bg: '#F0F3F7', border: '#DDE4EE' },
  memory_search: { Icon: MemorySearchIcon, color: '#6D4AFF', bg: '#F0EDFF', border: '#DCD4FF' },
  memory_get: { Icon: MemoryGetIcon, color: '#4B5563', bg: '#F1F3F5', border: '#DEE3E8' },
  scheduler: { Icon: SchedulerIcon, color: '#B45309', bg: '#FFF4E6', border: '#F5D3A1' },
  env_config: { Icon: EnvConfigIcon, color: '#475569', bg: '#F2F5F8', border: '#DEE5ED' },
};

const genericToolDefinition: ToolIconDefinition = {
  Icon: GenericToolIcon,
  color: '#475569',
  bg: '#F2F5F8',
  border: '#DEE5ED',
};

function renderStepIcon(
  definition: ToolIconDefinition,
  status: ToolIconStatus,
  extraClassName?: string,
) {
  const Icon = definition.Icon;
  const style = {
    '--tool-icon-color': definition.color,
    '--tool-icon-bg': definition.bg,
    '--tool-icon-border': definition.border,
  } as CSSProperties;
  const className = [
    'chat-tool-step-icon',
    `chat-tool-step-icon--${status}`,
    extraClassName,
  ].filter(Boolean).join(' ');

  return (
    <span className={className} style={style} aria-hidden="true">
      <Icon />
    </span>
  );
}

function resolveToolIconKey(toolName?: string): ToolIconKey | undefined {
  const normalized = (toolName || '')
    .trim()
    .toLowerCase()
    .replace(/[^\w]+/g, '_')
    .replace(/^_+|_+$/g, '');

  if (!normalized) return undefined;
  if (normalized in toolIconDefinitions) return normalized as ToolIconKey;

  if (normalized.includes('memory') && normalized.includes('search')) return 'memory_search';
  if (normalized.includes('memory') && (normalized.includes('get') || normalized.includes('read'))) return 'memory_get';
  if (normalized.includes('web') && (normalized.includes('fetch') || normalized.includes('url'))) return 'web_fetch';
  if (normalized.includes('env') || normalized.includes('config')) return 'env_config';
  if (normalized.includes('schedule') || normalized.includes('cron')) return 'scheduler';
  if (normalized.includes('browser')) return 'browser';
  if (normalized.includes('vision') || normalized.includes('image')) return 'vision';
  if (normalized.includes('bash') || normalized.includes('shell') || normalized.includes('terminal')) return 'bash';
  if (normalized === 'list' || normalized === 'dir') return 'ls';

  return undefined;
}

export function renderToolStepIcon(toolName: string | undefined, status: ToolIconStatus) {
  const iconKey = resolveToolIconKey(toolName);
  const definition = iconKey ? toolIconDefinitions[iconKey] : genericToolDefinition;
  return renderStepIcon(definition, status);
}

const reasoningIconDefinition: ToolIconDefinition = {
  Icon: ReasoningIcon,
  color: '#61DAFB',
  bg: '#E6F9FF',
  border: '#BDEFFF',
};

export function renderReasoningStepIcon(status: ToolIconStatus) {
  return renderStepIcon(reasoningIconDefinition, status, 'chat-reasoning-step-icon');
}
