const palette = {
  brand: {
    50: '#eff4ff',
    100: '#dbe6ff',
    500: '#1a6ff5',
    600: '#1558cc',
    700: '#1042a3',
  },
  neutral: {
    0: '#ffffff',
    25: '#fafbfc',
    50: '#f5f7fa',
    75: '#eef1f6',
    100: '#e4e8ee',
    600: '#4b5362',
    800: '#1f2430',
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
  md: 34,
  lg: 40,
};

const typography = {
  fontFamily: '"PingFang SC", "Microsoft YaHei", "Noto Sans SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  fontSize: 14,
  fontSizeLG: 16,
  fontSizeSM: 12,
  lineHeight: 1.5,
};

const shadow = {
  card: '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 3px 0 rgba(0, 0, 0, 0.04)',
  raised: '0 4px 6px -1px rgba(0, 0, 0, 0.04), 0 2px 4px -2px rgba(0, 0, 0, 0.04)',
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
    colorPrimary: palette.brand[500],
    colorSuccess: palette.semantic.success,
    colorWarning: palette.semantic.warning,
    colorError: palette.semantic.error,
    colorInfo: palette.brand[500],
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
    colorBorder: palette.neutral[100],
    colorBorderSecondary: palette.neutral[75],
    colorText: palette.neutral[800],
    colorTextSecondary: palette.neutral[600],
    colorTextTertiary: '#8891a0',
    boxShadow: shadow.card,
    boxShadowSecondary: shadow.raised,
    wireframe: false,
  },
  components: {
    Menu: {
      itemBorderRadius: radius.md,
      itemHeight: 36,
      itemMarginInline: 8,
      itemHoverBg: palette.neutral[50],
      itemSelectedBg: palette.brand[50],
      itemSelectedColor: palette.brand[500],
      itemActiveBg: palette.brand[50],
      iconSize: 18,
      collapsedIconSize: 18,
    },
    Card: {
      paddingLG: 20,
      borderRadiusLG: radius.lg,
    },
    Button: {
      borderRadius: radius.md,
      borderRadiusLG: 10,
      borderRadiusSM: radius.sm,
      controlHeight: controlHeight.md,
      controlHeightLG: controlHeight.lg,
      controlHeightSM: controlHeight.sm,
      fontWeight: 500,
    },
    Tag: {
      borderRadiusSM: radius.sm,
      fontSizeSM: 11,
      lineHeightSM: 1.4,
    },
    Table: {
      borderRadius: radius.md,
      borderColor: palette.neutral[100],
      headerBg: '#f8fafc',
      headerColor: palette.neutral[600],
      rowHoverBg: palette.neutral[50],
    },
    Input: {
      borderRadius: radius.md,
      borderRadiusLG: 10,
      borderRadiusSM: radius.sm,
    },
    Select: {
      borderRadius: radius.md,
      borderRadiusLG: 10,
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
