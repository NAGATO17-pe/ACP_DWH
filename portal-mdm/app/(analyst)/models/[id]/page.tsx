import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Sparkles, Target, TrendingUp } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { KpiCard } from "@/components/charts/kpi-card";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  MODELS,
  MODEL_STATUS_LABEL,
  type ModelStatus,
} from "@/lib/mock/models";
import { formatDate, formatNumber } from "@/lib/format";
import { ModelDetailCharts } from "./model-detail-charts";

const STATUS_VARIANT: Record<ModelStatus, "success" | "warning" | "default"> = {
  produccion: "success",
  staging: "warning",
  archivado: "default",
};

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ModelDetailPage({ params }: PageProps) {
  const { id } = await params;
  const model = MODELS.find((m) => m.id === id);
  if (!model) notFound();

  return (
    <div className="flex flex-col gap-6">
      <Button asChild variant="ghost" size="sm" className="self-start">
        <Link href="/models">
          <ArrowLeft aria-hidden className="h-4 w-4" />
          Volver al catálogo
        </Link>
      </Button>

      <PageHeader
        title={model.name}
        description={`${model.algorithm} · target: ${model.target}`}
        actions={
          <Badge variant={STATUS_VARIANT[model.status]}>
            {MODEL_STATUS_LABEL[model.status]}
          </Badge>
        }
      />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Accuracy"
          value={`${(model.accuracy * 100).toFixed(1)}`}
          unit="%"
          icon={Target}
          tone="success"
        />
        <KpiCard
          label="AUC"
          value={model.auc.toFixed(2)}
          icon={TrendingUp}
        />
        <KpiCard label="F1 Score" value={model.f1.toFixed(2)} />
        <KpiCard
          label="Predicciones (24h)"
          value={formatNumber(model.predictions24h)}
          icon={Sparkles}
        />
      </section>

      <Tabs defaultValue="metrics">
        <TabsList>
          <TabsTrigger value="metrics">Métricas</TabsTrigger>
          <TabsTrigger value="features">Importancia de variables</TabsTrigger>
          <TabsTrigger value="confusion">Matriz de confusión</TabsTrigger>
        </TabsList>

        <TabsContent value="metrics">
          <Card>
            <CardHeader>
              <CardTitle>Curva ROC</CardTitle>
              <CardDescription>
                Trade-off entre tasa de verdaderos positivos y falsos
                positivos.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ModelDetailCharts kind="roc" />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="features">
          <Card>
            <CardHeader>
              <CardTitle>Variables más relevantes</CardTitle>
              <CardDescription>
                Importancia relativa según el modelo entrenado.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ModelDetailCharts kind="features" />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="confusion">
          <Card>
            <CardHeader>
              <CardTitle>Matriz de confusión</CardTitle>
              <CardDescription>
                Distribución de predicciones contra valores reales.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ModelDetailCharts kind="confusion" />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle>Información del modelo</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                ID
              </dt>
              <dd className="font-mono text-sm">{model.id}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                Algoritmo
              </dt>
              <dd className="text-sm">{model.algorithm}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                Target
              </dt>
              <dd className="text-sm">{model.target}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                Entrenado
              </dt>
              <dd className="tabular-nums text-sm">
                {formatDate(model.trainedAt)}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
