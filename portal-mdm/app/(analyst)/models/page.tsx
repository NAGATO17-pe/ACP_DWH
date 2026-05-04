import type { Metadata } from "next";
import Link from "next/link";
import { ChevronRight, FlaskConical, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  MODELS,
  MODEL_STATUS_LABEL,
  type ModelStatus,
} from "@/lib/mock/models";
import { formatDate, formatNumber } from "@/lib/format";

const STATUS_VARIANT: Record<
  ModelStatus,
  "success" | "warning" | "default"
> = {
  produccion: "success",
  staging: "warning",
  archivado: "default",
};

export const metadata: Metadata = { title: "Modelos predictivos" };

export default function ModelsListPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Modelos predictivos"
        description="Catálogo de modelos analíticos disponibles para exploración y reporte."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {MODELS.map((model) => (
          <Link
            key={model.id}
            href={`/models/${model.id}`}
            className="block focus-visible:outline-none"
          >
            <Card className="hover:border-[var(--color-primary)] transition-colors">
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <span
                      aria-hidden
                      className="bg-[var(--color-surface-2)] text-[var(--color-primary)] inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md"
                    >
                      <FlaskConical className="h-4 w-4" />
                    </span>
                    <div className="flex flex-col gap-1">
                      <CardTitle>{model.name}</CardTitle>
                      <CardDescription>
                        {model.algorithm} · target: {model.target}
                      </CardDescription>
                    </div>
                  </div>
                  <Badge variant={STATUS_VARIANT[model.status]}>
                    {MODEL_STATUS_LABEL[model.status]}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="flex items-center justify-between">
                <dl className="grid grid-cols-3 gap-4">
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                      Accuracy
                    </dt>
                    <dd className="tabular-nums text-lg font-semibold">
                      {(model.accuracy * 100).toFixed(1)}%
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                      AUC
                    </dt>
                    <dd className="tabular-nums text-lg font-semibold">
                      {model.auc.toFixed(2)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                      F1
                    </dt>
                    <dd className="tabular-nums text-lg font-semibold">
                      {model.f1.toFixed(2)}
                    </dd>
                  </div>
                </dl>
                <ChevronRight
                  aria-hidden
                  className="h-5 w-5 text-[var(--color-text-muted)]"
                />
              </CardContent>
              <div className="flex items-center justify-between border-t border-[var(--color-border)] px-5 py-3 text-xs text-[var(--color-text-muted)]">
                <span className="inline-flex items-center gap-1.5">
                  <Sparkles aria-hidden className="h-3.5 w-3.5" />
                  {formatNumber(model.predictions24h)} predicciones (24h)
                </span>
                <span className="tabular-nums">
                  Entrenado {formatDate(model.trainedAt)}
                </span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
