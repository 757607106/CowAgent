const palette = {
  brand: {
    50: '#F0F5FF',
    100: '#E5EDFF',
    200: '#CDDBFF',
    300: '#B4C6FF',
    400: '#94AFFF',
    500: '#688AF8',
    600: '#4D6BFE',
    700: '#3A52D9',
    800: '#2A3B9F',
  },
  neutral: {
    0: '#ffffff',
    25: '#fafbfc',
    50: '#f7f8fa',
    75: '#f1f3f5',
    100: '#eceef1',
    200: '#e0e3e8',
    300: '#cfd4dc',
    400: '#9ba3af',
    500: '#6d7684',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },
  semantic: {
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
  },
};
const radius = {
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
};

const controlHeight = {
  sm: 28,
  md: 36,
  lg: 44,
};

const typography = {
  fontFamily: '"Inter", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  fontSize: 14,
  fontSizeLG: 16,
  fontSizeSM: 12,
  lineHeight: 1.5714285714285714,
};

const shadow = {
  card: '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 3px 0 rgba(0, 0, 0, 0.04)',
  raised: '0 4px 6px -1px rgba(0, 0, 0, 0.04), 0 2px 4px -2px rgba(0, 0, 0, 0.02), 0 0 0 1px rgba(0,0,0,0.03)',
  floating: '0 10px 15px -3px rgba(0, 0, 0, 0.06), 0 4px 6px -4px rgba(0, 0, 0, 0.03), 0 0 0 1px rgba(0,0,0,0.03)',
};

export const consoleThemeTokens = {
  palette,
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
    colorInfo: palette.brand[600],
    borderRadius: radius.md,
    borderRadiusLG: radius.lg,
    borderRadiusSM: radius.sm,
    ...typography,
    controlHeight: controlHeight.md,
    controlHeightLG: controlHeight.lg,
    controlHeightSM: controlHeight.sm,
    paddingContentHorizontal: 16,
    paddingContentVertical: 12,
    colorBgContainer: palette.neutral[0],
    colorBgElevated: palette.neutral[0],
    colorBgLayout: palette.neutral[50],
    colorBorder: palette.neutral[200],
    colorBorderSecondary: palette.neutral[100],
    colorText: palette.neutral[900],
    colorTextSecondary: palette.neutral[600],
    colorTextTertiary: palette.neutral[400],
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
      itemHoverBg: 'transparent',
      itemSelectedBg: palette.neutral[100],
      itemSelectedColor: palette.neutral[900],
      itemActiveBg: 'transparent',
      iconSize: 18,
      collapsedIconSize: 18,
    },
    Card: {
      paddingLG: 20,
      borderRadiusLG: radius.xl,
      boxShadow: shadow.card,
      colorBorderSecondary: 'rgba(0, 0, 0, 0.04)',
    },
    Button: {
      borderRadius: radius.md,
      borderRadiusLG: radius.lg,
      borderRadiusSM: radius.sm,
      controlHeight: controlHeight.md,
      controlHeightLG: controlHeight.lg,
      controlHeightSM: controlHeight.sm,
      fontWeight: 500,
      primaryShadow: '0 1px 2px rgba(104, 138, 248, 0.4)',
      defaultShadow: shadow.card,
    },
    Tag: {
      borderRadiusSM: radius.sm,
      fontSizeSM: 12,
      lineHeightSM: 1.5,
      defaultBg: palette.neutral[50],
      defaultColor: palette.neutral[700],
    },
    Table: {
      borderRadius: radius.lg,
      borderColor: 'rgba(0, 0, 0, 0.04)',
      headerBg: 'transparent',
      headerColor: palette.neutral[500],
      rowHoverBg: palette.neutral[25],
      headerBorderRadius: 0,
      padding: 10,
    },
    Input: {
      borderRadius: radius.md,
      borderRadiusLG: radius.lg,
      borderRadiusSM: radius.sm,
      colorBorder: palette.neutral[200],
      hoverBorderColor: palette.brand[400],
      activeBorderColor: palette.brand[600],
    },
    Select: {
      borderRadius: radius.md,
      borderRadiusLG: radius.lg,
      borderRadiusSM: radius.sm,
      colorBorder: palette.neutral[200],
    },
    Modal: {
      borderRadiusLG: radius.xl,
      titleFontSize: 18,
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
  const set = (name: string, value: string) => {
    root.style.setProperty(name, value);
  };

  for (const [key, value] of Object.entries(palette.brand)) {
    set(`--brand-${key}`, value);
  }

  for (const [key, value] of Object.entries(palette.neutral)) {
    set(`--neutral-${key}`, value);
  }

  set('--color-primary', palette.brand[600]);
  set('--color-primary-hover', palette.brand[700]);
  set('--color-primary-pressed', palette.brand[800]);
  set('--color-primary-light', palette.brand[50]);
  set('--color-primary-border', palette.brand[100]);
  set('--color-success', palette.semantic.success);
  set('--color-warning', palette.semantic.warning);
  set('--color-error', palette.semantic.error);

  set('--radius-sm', `${radius.sm}px`);
  set('--radius-md', `${radius.md}px`);
  set('--radius-lg', `${radius.lg}px`);
  set('--radius-xl', `${radius.xl}px`);
}
