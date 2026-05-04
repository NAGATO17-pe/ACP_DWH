import type { Metadata } from "next";
import { CheckCircle2, FileSearch2, ShieldAlert, Target } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { KpiCard } from "@/components/charts/kpi-card";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { QUALITY_KPIS } from "@/lib/mock/quality";
import { formatNumber } from "@/lib/format";
import {
  QualityByEntityChart,
  QualityGauge,
  QualityRadarChart,
  QualityTrendChart,
} from "./quality-charts";

export const metadata: Metadata = { title: "Calidad de datos" };

export default function QualityPage() {
  const k = QUALITY_KPIS;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Calidad de datos"
        description="Indicadores clave del sistema MDM y desglose por entidad."
      />

      <section
        aria-label="KPIs principales"
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <KpiCard
          label="Completitud global"
          value={k.completeness.toFixed(1)}
          unit="%"
          delta={k.deltas.completeness}
          deltaLabel="vs. mes anterior"
          icon={Target}
          tone="success"
        />
        <KpiCard
          label="Validados"
          value={k.validated.toFixed(1)}
          unit="%"
          delta={k.deltas.validated}
          deltaLabel="vs. mes anterior"
          icon={CheckCircle2}
          tone="success"
        />
        <KpiCard
          label="Errores activos"
          value={formatNumber(k.activeErrors)}
          delta={k.deltas.activeErrors}
          deltaLabel="vs. mes anterior"
          icon={ShieldAlert}
          tone="destructive"
        />
        <KpiCard
          label="Score global"
          value={k.globalScore}
          unit="/100"
          delta={k.deltas.globalScore}
          deltaLabel="vs. mes anterior"
          icon={FileSearch2}
        />
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Calidad por entidad — Target vs Actual</CardTitle>
            <CardDescription>
              Comparativa de cumplimiento de calidad contra el target por tipo
              de entidad.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <QualityByEntityChart />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Score global</CardTitle>
            <CardDescription>
              Indicador agregado de calidad maestra.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center gap-2">
              <span className="tabular-nums text-5xl font-bold text-[var(--color-primary)]">
                {k.globalScore}
              </span>
              <span className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                de 100
              </span>
            </div>
            <QualityGauge score={k.globalScore} />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Evolución temporal de errores</CardTitle>
            <CardDescription>
              Errores detectados y registros validados en los últimos 12 meses.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <QualityTrendChart />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Comparativa multidimensional</CardTitle>
            <CardDescription>
              Desempeño por dimensión de calidad y entidad.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <QualityRadarChart />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
