const palette = {
  brand: {
    50:  '#EEEFFE',   /* Very light indigo tint */
    100: '#E0E1FD',
    200: '#C3C5FB',
    300: '#9FA2F8',
    400: '#7577F2',
    500: '#5557E8',
    600: '#4338CA',   /* Primary: indigo-600 — distinctive, not generic blue */
    700: '#3730A3',   /* Hover/pressed */
    800: '#2E2880',
  },
  accent: {
    50: '#FFF8E6',
    100: '#FFECC2',
    200: '#FFD98A',
    300: '#FFC15A',
    400: '#F5A524',
    500: '#D88910',
    600: '#B86B00',
    700: '#8F4F00',
  },
  neutral: {
    0: '#ffffff',
    25: '#FCFCFD',
    50: '#F6F7F9',
    75: '#EFF2F6',
    100: '#E8ECF2',
    200: '#D9DFEA',
    300: '#C2CAD8',
    400: '#8D98AB',
    500: '#606B80',
    600: '#475266',
    700: '#30394C',
    800: '#1F2735',
    900: '#121825',
  },
  semantic: {
    success: '#0F9F6E',
    warning: '#B86B00',
    error: '#D92D20',
    info: '#2F54D4',
  },
};

const surface = {
  body: '#F4F4F5',     /* Near-neutral warm grey, not the blue-tinted #F2F5F9 */
  surface: palette.neutral[0],
  raised: '#FFFFFF',
  subtle: '#FAFAFA',
  inset: '#F0F0F1',
};

const text = {
  primary: palette.neutral[900],
  secondary: palette.neutral[600],
  tertiary: palette.neutral[400],
  disabled: palette.neutral[300],
};

const border = {
  light: palette.neutral[100],
  default: palette.neutral[200],
  strong: palette.neutral[300],
  panel: 'rgba(18, 24, 37, 0.12)',
};

const radius = {
  xs: 4,
  sm: 6,
  md: 8,
  lg: 10,
  xl: 14,
  '2xl': 18,
  full: 999,
};

const controlHeight = {
  sm: 28,
  md: 36,
  lg: 44,
};

const typography = {
  /*
   * Inter is the standard for premium PC tools (Linear, Vercel, Raycast).
   * PingFang SC handles Chinese. Aptos/Segoe fallback for Windows.
   */
  fontFamily: '"Inter", "PingFang SC", "Microsoft YaHei UI", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  fontSize: 14,
  fontSizeLG: 16,
  fontSizeSM: 12,
  lineHeight: 1.5714285714285714,
};

const monoFont = '"JetBrains Mono", "Fira Code", "SF Mono", ui-monospace, "Cascadia Code", Menlo, Monaco, monospace';

const shadow = {
  xs: '0 1px 2px rgba(18, 24, 37, 0.04)',
  sm: '0 1px 2px rgba(18, 24, 37, 0.05), 0 10px 26px -22px rgba(18, 24, 37, 0.38)',
  md: '0 1px 3px rgba(18, 24, 37, 0.07), 0 18px 38px -28px rgba(18, 24, 37, 0.48)',
  lg: '0 1px 3px rgba(18, 24, 37, 0.08), 0 24px 48px -30px rgba(18, 24, 37, 0.54)',
  xl: '0 1px 4px rgba(18, 24, 37, 0.10), 0 32px 72px -36px rgba(18, 24, 37, 0.60)',
  card: '0 1px 2px rgba(18, 24, 37, 0.06), 0 12px 30px -24px rgba(18, 24, 37, 0.36)',
  raised: '0 1px 3px rgba(18, 24, 37, 0.08), 0 22px 48px -30px rgba(18, 24, 37, 0.52)',
  floating: '0 1px 4px rgba(18, 24, 37, 0.10), 0 30px 72px -34px rgba(18, 24, 37, 0.58)',
  focus: `0 0 0 2px ${palette.brand[100]}`,
};

export const consoleThemeTokens = {
  palette,
  surface,
  text,
  border,
  radius,
  controlHeight,
  typography,
  shadow,
};

export const appTheme = {
  token: {
    colorPrimary: palette.brand[600],
    colorSuccess: palette.semantic.success,
    colorWarning: palette.semantic.warning,
    colorError: palette.semantic.error,
    colorInfo: palette.semantic.info,
    borderRadius: radius.md,
    borderRadiusLG: radius.lg,
    borderRadiusSM: radius.sm,
    ...typography,
    controlHeight: controlHeight.md,
    controlHeightLG: controlHeight.lg,
    controlHeightSM: controlHeight.sm,
    paddingContentHorizontal: 16,
    paddingContentVertical: 12,
    colorBgContainer: surface.surface,
    colorBgElevated: surface.raised,
    colorBgLayout: surface.body,
    colorFillAlter: surface.subtle,
    colorFillSecondary: surface.inset,
    colorBorder: border.default,
    colorBorderSecondary: border.light,
    colorText: text.primary,
    colorTextSecondary: text.secondary,
    colorTextTertiary: text.tertiary,
    boxShadow: shadow.card,
    boxShadowSecondary: shadow.raised,
    boxShadowTertiary: shadow.floating,
    wireframe: false,
  },
  components: {
    Menu: {
      itemBorderRadius: radius.md,
      itemHeight: 38,
      itemMarginInline: 12,
      itemHoverBg: palette.neutral[75],
      itemSelectedBg: palette.brand[50],
      itemSelectedColor: palette.neutral[900],
      itemActiveBg: palette.brand[50],
      iconSize: 18,
      collapsedIconSize: 18,
    },
    Card: {
      paddingLG: 16,
      borderRadiusLG: radius.md,
      boxShadow: shadow.card,
      colorBorderSecondary: border.light,
    },
    Button: {
      borderRadius: radius.md,
      borderRadiusLG: radius.lg,
      borderRadiusSM: radius.sm,
      controlHeight: controlHeight.md,
      controlHeightLG: controlHeight.lg,
      controlHeightSM: controlHeight.sm,
      fontWeight: 500,
      primaryShadow: `0 1px 2px ${palette.brand[200]}`,
      defaultShadow: shadow.xs,
    },
    Tag: {
      borderRadiusSM: radius.sm,
      fontSizeSM: 12,
      lineHeightSM: 1.5,
      defaultBg: surface.subtle,
      defaultColor: text.secondary,
    },
    Table: {
      borderRadius: radius.lg,
      borderColor: border.light,
      headerBg: surface.subtle,
      headerColor: text.secondary,
      rowHoverBg: palette.brand[50],
      headerBorderRadius: 0,
      padding: 11,
    },
    Input: {
      borderRadius: radius.md,
      borderRadiusLG: radius.lg,
      borderRadiusSM: radius.sm,
      colorBorder: border.default,
      hoverBorderColor: palette.brand[400],
      activeBorderColor: palette.brand[600],
    },
    Select: {
      borderRadius: radius.md,
      borderRadiusLG: radius.lg,
      borderRadiusSM: radius.sm,
      colorBorder: border.default,
    },
    Modal: {
      borderRadiusLG: radius.md,
      titleFontSize: 16,
    },
    Drawer: {
      borderRadiusLG: 0,
    },
    Collapse: {
      borderRadiusLG: radius.lg,
      contentPadding: '16px 20px',
      headerPadding: '14px 20px',
    },
    Form: {
      itemMarginBottom: 16,
      labelFontSize: 13,
    },
    Switch: {
      trackHeight: 22,
      trackMinWidth: 40,
      handleSize: 18,
    },
    Tooltip: {
      borderRadius: radius.md,
    },
    Popover: {
      borderRadius: radius.lg,
    },
  },
};

export function applyConsoleThemeToCssVars(root: HTMLElement = document.documentElement) {
  const set = (name: string, value: string | number) => {
    root.style.setProperty(name, String(value));
  };

  const setEntries = (prefix: string, values: Record<string, string | number>) => {
    for (const [key, value] of Object.entries(values)) {
      set(`--${prefix}-${key}`, value);
    }
  };

  setEntries('brand', palette.brand);
  setEntries('accent', palette.accent);
  setEntries('neutral', palette.neutral);
  setEntries('radius', {
    xs: `${radius.xs}px`,
    sm: `${radius.sm}px`,
    md: `${radius.md}px`,
    lg: `${radius.lg}px`,
    xl: `${radius.xl}px`,
    '2xl': `${radius['2xl']}px`,
    full: `${radius.full}px`,
  });

  set('--bg-body', surface.body);
  set('--bg-surface', surface.surface);
  set('--bg-surface-raised', surface.raised);
  set('--bg-subtle', surface.subtle);
  set('--bg-inset', surface.inset);
  set('--text-primary', text.primary);
  set('--text-secondary', text.secondary);
  set('--text-tertiary', text.tertiary);
  set('--text-disabled', text.disabled);
  set('--border-light', border.light);
  set('--border-default', border.default);
  set('--border-strong', border.strong);
  set('--console-panel-border', border.panel);

  set('--color-primary', palette.brand[600]);
  set('--color-primary-hover', palette.brand[700]);
  set('--color-primary-pressed', palette.brand[800]);
  set('--color-primary-light', palette.brand[50]);
  set('--color-primary-border', palette.brand[100]);
  set('--color-accent', palette.accent[500]);
  set('--color-accent-light', palette.accent[50]);
  set('--color-accent-border', palette.accent[200]);
  set('--color-success', palette.semantic.success);
  set('--color-success-light', '#ECFDF3');
  set('--color-warning', palette.semantic.warning);
  set('--color-warning-light', palette.accent[50]);
  set('--color-error', palette.semantic.error);
  set('--color-error-light', '#FEF2F2');
  set('--color-info', palette.semantic.info);
  set('--color-info-light', '#EFF6FF');
  set('--on-dark-divider', 'rgba(255, 255, 255, 0.08)');
  set('--on-dark-grid-line', 'rgba(255, 255, 255, 0.06)');
  set('--on-primary-code-bg', 'rgba(0, 0, 0, 0.20)');
  set('--on-primary-border', 'rgba(255, 255, 255, 0.30)');
  set('--on-primary-chip-bg', 'rgba(255, 255, 255, 0.18)');
  set('--on-primary-link-underline', 'rgba(255, 255, 255, 0.60)');
  set('--on-primary-inline-code-bg', 'rgba(255, 255, 255, 0.20)');

  set('--shadow-none', 'none');
  set('--shadow-xs', shadow.xs);
  set('--shadow-sm', shadow.sm);
  set('--shadow-md', shadow.md);
  set('--shadow-lg', shadow.lg);
  set('--shadow-xl', shadow.xl);
  set('--shadow-card', shadow.card);
  set('--shadow-card-hover', shadow.raised);
  set('--console-panel-shadow', shadow.card);
  set('--console-panel-shadow-hover', shadow.raised);
  set('--focus-ring', shadow.focus);

  set('--font-sans', typography.fontFamily);
  set('--font-mono', monoFont);
}
