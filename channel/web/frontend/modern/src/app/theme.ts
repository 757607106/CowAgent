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
      itemHoverBg: palette.neutral[75],
      itemSelectedBg: palette.brand[50],
      itemSelectedColor: palette.brand[600],
      itemActiveBg: palette.brand[50],
      iconSize: 18,
      collapsedIconSize: 18,
    },
    Card: {
      paddingLG: 24,
      borderRadiusLG: radius.lg,
    },
    Button: {
      borderRadius: radius.md,
      borderRadiusLG: radius.lg,
      borderRadiusSM: radius.sm,
      controlHeight: controlHeight.md,
      controlHeightLG: controlHeight.lg,
      controlHeightSM: controlHeight.sm,
      fontWeight: 500,
    },
    Tag: {
      borderRadiusSM: radius.sm,
      fontSizeSM: 12,
      lineHeightSM: 1.5,
    },
    Table: {
      borderRadius: radius.md,
      borderColor: palette.neutral[100],
      headerBg: palette.neutral[50],
      headerColor: palette.neutral[600],
      rowHoverBg: palette.neutral[25],
    },
    Input: {
      borderRadius: radius.md,
      borderRadiusLG: radius.lg,
      borderRadiusSM: radius.sm,
    },
    Select: {
      borderRadius: radius.md,
      borderRadiusLG: radius.lg,
      borderRadiusSM: radius.sm,
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
      itemMarginBottom: 20,
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
