"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RECHARTS_THEME } from "@/components/charts/recharts-theme";
import {
  QUALITY_BY_ENTITY,
  QUALITY_RADAR,
  QUALITY_TREND,
} from "@/lib/mock/quality";

const TOOLTIP_STYLE = {
  contentStyle: {
    background: RECHARTS_THEME.surface,
    border: `1px solid ${RECHARTS_THEME.border}`,
    borderRadius: 8,
    fontSize: 12,
    color: "#F8FAFC",
  },
  labelStyle: { color: RECHARTS_THEME.textMuted },
} as const;

export function QualityByEntityChart() {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart
        data={QUALITY_BY_ENTITY}
        margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
      >
        <CartesianGrid stroke={RECHARTS_THEME.border} strokeDasharray="3 3" />
        <XAxis dataKey="entity" stroke={RECHARTS_THEME.textMuted} fontSize={12} />
        <YAxis stroke={RECHARTS_THEME.textMuted} fontSize={12} domain={[0, 100]} />
        <Tooltip {...TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar
          dataKey="target"
          name="Target"
          fill={RECHARTS_THEME.border}
          radius={[4, 4, 0, 0]}
        />
        <Bar
          dataKey="actual"
          name="Actual"
          fill={RECHARTS_THEME.primary}
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function QualityTrendChart() {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart
        data={QUALITY_TREND}
        margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
      >
        <defs>
          <linearGradient id="errors-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={RECHARTS_THEME.destructive} stopOpacity={0.4} />
            <stop offset="100%" stopColor={RECHARTS_THEME.destructive} stopOpacity={0} />
          </linearGradient>
          <linearGradient id="validated-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={RECHARTS_THEME.success} stopOpacity={0.4} />
            <stop offset="100%" stopColor={RECHARTS_THEME.success} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={RECHARTS_THEME.border} strokeDasharray="3 3" />
        <XAxis dataKey="date" stroke={RECHARTS_THEME.textMuted} fontSize={12} />
        <YAxis stroke={RECHARTS_THEME.textMuted} fontSize={12} />
        <Tooltip {...TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area
          type="monotone"
          dataKey="errors"
          name="Errores"
          stroke={RECHARTS_THEME.destructive}
          fill="url(#errors-grad)"
          strokeWidth={2}
        />
        <Area
          type="monotone"
          dataKey="validated"
          name="Validados"
          stroke={RECHARTS_THEME.success}
          fill="url(#validated-grad)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function QualityRadarChart() {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={QUALITY_RADAR}>
        <PolarGrid stroke={RECHARTS_THEME.border} />
        <PolarAngleAxis
          dataKey="metric"
          stroke={RECHARTS_THEME.textMuted}
          fontSize={11}
        />
        <Tooltip {...TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Radar
          name="Clientes"
          dataKey="Clientes"
          stroke={RECHARTS_THEME.primary}
          fill={RECHARTS_THEME.primary}
          fillOpacity={0.25}
        />
        <Radar
          name="Productos"
          dataKey="Productos"
          stroke={RECHARTS_THEME.success}
          fill={RECHARTS_THEME.success}
          fillOpacity={0.2}
        />
        <Radar
          name="Proveedores"
          dataKey="Proveedores"
          stroke={RECHARTS_THEME.warning}
          fill={RECHARTS_THEME.warning}
          fillOpacity={0.2}
        />
        <Radar
          name="Ubicaciones"
          dataKey="Ubicaciones"
          stroke={RECHARTS_THEME.info}
          fill={RECHARTS_THEME.info}
          fillOpacity={0.2}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}

export function QualityGauge({ score }: { score: number }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        layout="vertical"
        data={[{ name: "score", score, rest: 100 - score }]}
        margin={{ top: 10, right: 16, left: 16, bottom: 10 }}
        stackOffset="expand"
      >
        <XAxis type="number" hide domain={[0, 100]} />
        <YAxis type="category" dataKey="name" hide />
        <Bar
          dataKey="score"
          stackId="a"
          fill={RECHARTS_THEME.primary}
          radius={[6, 0, 0, 6]}
        />
        <Bar
          dataKey="rest"
          stackId="a"
          fill={RECHARTS_THEME.border}
          radius={[0, 6, 6, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
