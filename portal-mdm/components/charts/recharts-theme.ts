/**
 * Recharts theme tokens — sourced from CSS vars at runtime in the browser
 * but with safe fallbacks for SSR.
 */
export const RECHARTS_THEME = {
  primary: "#2563EB",
  primary2: "#0369A1",
  success: "#059669",
  warning: "#D97706",
  destructive: "#DC2626",
  info: "#0284C7",
  textMuted: "#94A3B8",
  border: "#1E3A5F",
  surface: "#1E293B",
} as const;
