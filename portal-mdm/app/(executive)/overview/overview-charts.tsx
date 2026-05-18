"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RECHARTS_THEME } from "@/components/charts/recharts-theme";
import { QUALITY_BY_ENTITY, QUALITY_TREND } from "@/lib/mock/quality";

const TOOLTIP_STYLE = {
  contentStyle: {
    background: RECHARTS_THEME.surface,
    border: `1px solid ${RECHARTS_THEME.border}`,
    borderRadius: 8,
    fontSize: 12,
    color: "#F8FAFC",
  },
} as const;

export function ExecutiveTrendChart() {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={QUALITY_TREND} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="exec-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={RECHARTS_THEME.primary} stopOpacity={0.5} />
            <stop offset="100%" stopColor={RECHARTS_THEME.primary} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={RECHARTS_THEME.border} strokeDasharray="3 3" />
        <XAxis dataKey="date" stroke={RECHARTS_THEME.textMuted} fontSize={12} />
        <YAxis stroke={RECHARTS_THEME.textMuted} fontSize={12} />
        <Tooltip {...TOOLTIP_STYLE} />
        <Area
          type="monotone"
          dataKey="validated"
          name="Validados"
          stroke={RECHARTS_THEME.primary}
          fill="url(#exec-grad)"
          strokeWidth={3}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function ExecutiveByEntityChart() {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={QUALITY_BY_ENTITY}
        margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
      >
        <CartesianGrid stroke={RECHARTS_THEME.border} strokeDasharray="3 3" />
        <XAxis dataKey="entity" stroke={RECHARTS_THEME.textMuted} fontSize={12} />
        <YAxis stroke={RECHARTS_THEME.textMuted} fontSize={12} domain={[0, 100]} />
        <Tooltip {...TOOLTIP_STYLE} />
        <Bar
          dataKey="actual"
          name="Calidad"
          fill={RECHARTS_THEME.primary}
          radius={[6, 6, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
