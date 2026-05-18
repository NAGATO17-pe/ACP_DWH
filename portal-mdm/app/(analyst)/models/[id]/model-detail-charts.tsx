"use client";

import { PlotlyChart } from "@/components/charts/plotly-wrapper";
import { RECHARTS_THEME } from "@/components/charts/recharts-theme";

const ROC_X = Array.from({ length: 21 }, (_, i) => i / 20);
const ROC_Y = ROC_X.map((x) => Math.min(1, Math.pow(x, 0.35) + 0.05));

const FEATURE_NAMES = [
  "Tiempo de antigüedad",
  "Frecuencia de compras",
  "Ticket promedio",
  "Días desde última compra",
  "Categoría preferida",
  "Canal principal",
  "Región geográfica",
  "Score crediticio",
];

const FEATURE_VALUES = [0.32, 0.21, 0.16, 0.12, 0.08, 0.05, 0.04, 0.02];

const CONFUSION = [
  [842, 38],
  [62, 458],
];

export function ModelDetailCharts({
  kind,
}: {
  kind: "roc" | "features" | "confusion";
}) {
  if (kind === "roc") {
    return (
      <PlotlyChart
        height={340}
        data={[
          {
            x: ROC_X,
            y: ROC_Y,
            type: "scatter",
            mode: "lines",
            name: "Modelo",
            line: { color: RECHARTS_THEME.primary, width: 3 },
            fill: "tozeroy",
            fillcolor: `${RECHARTS_THEME.primary}33`,
          },
          {
            x: [0, 1],
            y: [0, 1],
            type: "scatter",
            mode: "lines",
            name: "Aleatorio",
            line: { color: RECHARTS_THEME.textMuted, width: 1, dash: "dash" },
          },
        ]}
        layout={{
          xaxis: { title: { text: "Tasa de falsos positivos" }, range: [0, 1] },
          yaxis: { title: { text: "Tasa de verdaderos positivos" }, range: [0, 1] },
          showlegend: true,
          legend: { x: 0.65, y: 0.1 },
        }}
      />
    );
  }

  if (kind === "features") {
    return (
      <PlotlyChart
        height={340}
        data={[
          {
            x: FEATURE_VALUES,
            y: FEATURE_NAMES,
            type: "bar",
            orientation: "h",
            marker: { color: RECHARTS_THEME.primary },
          },
        ]}
        layout={{
          xaxis: { title: { text: "Importancia relativa" } },
          margin: { l: 180, r: 20, t: 20, b: 40 },
        }}
      />
    );
  }

  // confusion
  return (
    <PlotlyChart
      height={340}
      data={[
        {
          z: CONFUSION,
          x: ["Predicho: No", "Predicho: Sí"],
          y: ["Real: No", "Real: Sí"],
          type: "heatmap",
          colorscale: [
            [0, RECHARTS_THEME.surface],
            [1, RECHARTS_THEME.primary],
          ],
          showscale: true,
          texttemplate: "%{z}",
          textfont: { color: "#F8FAFC", size: 14 },
        },
      ]}
      layout={{ margin: { l: 80, r: 40, t: 20, b: 60 } }}
    />
  );
}
