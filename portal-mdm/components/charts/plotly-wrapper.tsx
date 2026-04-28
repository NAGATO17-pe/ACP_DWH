"use client";

import dynamic from "next/dynamic";
import type { Layout, Data, Config } from "plotly.js";
import { RECHARTS_THEME } from "./recharts-theme";

const Plot = dynamic(() => import("react-plotly.js"), {
  ssr: false,
  loading: () => (
    <div
      role="status"
      aria-busy="true"
      className="bg-[var(--color-surface-2)] flex h-64 w-full items-center justify-center rounded-md text-xs text-[var(--color-text-muted)]"
    >
      Cargando gráfico…
    </div>
  ),
});

interface PlotlyChartProps {
  data: Data[];
  layout?: Partial<Layout>;
  config?: Partial<Config>;
  height?: number;
  className?: string;
}

export function PlotlyChart({
  data,
  layout,
  config,
  height = 320,
  className,
}: PlotlyChartProps) {
  const themedLayout: Partial<Layout> = {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { family: "Inter, sans-serif", color: RECHARTS_THEME.textMuted, size: 12 },
    margin: { l: 50, r: 20, t: 30, b: 40 },
    xaxis: { gridcolor: RECHARTS_THEME.border, zerolinecolor: RECHARTS_THEME.border },
    yaxis: { gridcolor: RECHARTS_THEME.border, zerolinecolor: RECHARTS_THEME.border },
    colorway: [
      RECHARTS_THEME.primary,
      RECHARTS_THEME.success,
      RECHARTS_THEME.warning,
      RECHARTS_THEME.info,
      RECHARTS_THEME.destructive,
    ],
    ...layout,
  };

  return (
    <div className={className} style={{ height }}>
      <Plot
        data={data}
        layout={themedLayout}
        config={{ displaylogo: false, responsive: true, ...config }}
        style={{ width: "100%", height: "100%" }}
        useResizeHandler
      />
    </div>
  );
}
