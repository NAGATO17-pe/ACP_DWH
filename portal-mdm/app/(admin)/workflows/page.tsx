import type { Metadata } from "next";
import { Check, Clock, GitPullRequestArrow, X } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { KpiCard } from "@/components/charts/kpi-card";
import {
  WORKFLOWS,
  WORKFLOW_STATUS_LABEL,
  type WorkflowStatus,
} from "@/lib/mock/workflows";
import { formatDateTime } from "@/lib/format";

const STATUS_VARIANT: Record<
  WorkflowStatus,
  "warning" | "info" | "success" | "destructive"
> = {
  pendiente: "warning",
  "en-revision": "info",
  aprobado: "success",
  rechazado: "destructive",
};

const TYPE_LABEL: Record<"alta" | "modificacion" | "baja", string> = {
  alta: "Alta",
  modificacion: "Modificación",
  baja: "Baja",
};

const STEPPER_STEPS = [
  { key: "pendiente", label: "Pendiente" },
  { key: "en-revision", label: "En revisión" },
  { key: "aprobado", label: "Decisión" },
] as const;

function Stepper({ status }: { status: WorkflowStatus }) {
  const idx =
    status === "pendiente"
      ? 0
      : status === "en-revision"
        ? 1
        : 2;

  return (
    <ol className="flex items-center gap-3" aria-label="Progreso del workflow">
      {STEPPER_STEPS.map((step, i) => {
        const done = i < idx || (i === idx && status !== "pendiente");
        const current = i === idx;
        return (
          <li key={step.key} className="flex items-center gap-2">
            <span
              aria-hidden
              className={
                done
                  ? "bg-[var(--color-success)] text-white inline-flex h-6 w-6 items-center justify-center rounded-full text-xs"
                  : current
                    ? "bg-[var(--color-primary)] text-white inline-flex h-6 w-6 items-center justify-center rounded-full text-xs ring-2 ring-[var(--color-primary)]/30"
                    : "bg-[var(--color-surface-2)] text-[var(--color-text-muted)] inline-flex h-6 w-6 items-center justify-center rounded-full text-xs"
              }
            >
              {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
            </span>
            <span
              className={
                done || current
                  ? "text-xs font-medium"
                  : "text-xs text-[var(--color-text-muted)]"
              }
            >
              {step.label}
            </span>
            {i < STEPPER_STEPS.length - 1 ? (
              <span
                aria-hidden
                className={
                  done
                    ? "bg-[var(--color-success)] h-px w-8"
                    : "bg-[var(--color-border)] h-px w-8"
                }
              />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

export const metadata: Metadata = { title: "Workflows de aprobación" };

export default function WorkflowsPage() {
  const pending = WORKFLOWS.filter(
    (w) => w.status === "pendiente" || w.status === "en-revision",
  );
  const approved = WORKFLOWS.filter((w) => w.status === "aprobado").length;
  const rejected = WORKFLOWS.filter((w) => w.status === "rechazado").length;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Workflows de aprobación"
        description="Cola de solicitudes, revisión de cambios y acciones de aprobación."
      />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard
          label="En cola"
          value={pending.length}
          icon={Clock}
          tone="warning"
        />
        <KpiCard
          label="Aprobados (mes)"
          value={approved}
          icon={Check}
          tone="success"
        />
        <KpiCard
          label="Rechazados (mes)"
          value={rejected}
          icon={X}
          tone="destructive"
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Cola de pendientes</CardTitle>
          <CardDescription>
            Solicitudes esperando revisión o decisión final.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {pending.length === 0 ? (
            <p className="py-8 text-center text-sm text-[var(--color-text-muted)]">
              No hay workflows pendientes.
            </p>
          ) : (
            pending.map((wf) => (
              <article
                key={wf.id}
                className="bg-[var(--color-surface-2)]/40 flex flex-col gap-3 rounded-md border border-[var(--color-border)] p-4 lg:flex-row lg:items-center lg:justify-between"
              >
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <GitPullRequestArrow
                      aria-hidden
                      className="h-4 w-4 text-[var(--color-primary)]"
                    />
                    <span className="font-mono text-xs text-[var(--color-text-muted)]">
                      {wf.id}
                    </span>
                    <Badge variant="primary">{TYPE_LABEL[wf.type]}</Badge>
                    <Badge variant={STATUS_VARIANT[wf.status]}>
                      {WORKFLOW_STATUS_LABEL[wf.status]}
                    </Badge>
                  </div>
                  <p className="font-medium">{wf.entityName}</p>
                  <p className="text-xs text-[var(--color-text-muted)]">
                    {wf.changes} cambios · solicitado por {wf.requestedBy} ·{" "}
                    {formatDateTime(wf.createdAt)}
                  </p>
                  <div className="pt-1">
                    <Stepper status={wf.status} />
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="outline" size="sm">
                    Ver diff
                  </Button>
                  <Button variant="destructive" size="sm">
                    <X aria-hidden className="h-4 w-4" />
                    Rechazar
                  </Button>
                  <Button variant="success" size="sm">
                    <Check aria-hidden className="h-4 w-4" />
                    Aprobar
                  </Button>
                </div>
              </article>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Histórico reciente</CardTitle>
          <CardDescription>
            Workflows aprobados o rechazados en los últimos días.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="divide-y divide-[var(--color-border)]">
            {WORKFLOWS.filter(
              (w) => w.status === "aprobado" || w.status === "rechazado",
            ).map((wf) => (
              <li
                key={wf.id}
                className="flex items-center justify-between py-3"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-[var(--color-text-muted)]">
                    {wf.id}
                  </span>
                  <span className="text-sm">{wf.entityName}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {formatDateTime(wf.createdAt)}
                  </span>
                  <Badge variant={STATUS_VARIANT[wf.status]}>
                    {WORKFLOW_STATUS_LABEL[wf.status]}
                  </Badge>
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
