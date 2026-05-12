import type { Metadata } from "next";
import {
  Check,
  FilePlus,
  FilePenLine,
  LogIn,
  Trash2,
  X,
  type LucideIcon,
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  AUDIT_ACTION_LABEL,
  AUDIT_EVENTS,
  type AuditAction,
} from "@/lib/mock/audit";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const ICONS: Record<AuditAction, LucideIcon> = {
  creacion: FilePlus,
  modificacion: FilePenLine,
  aprobacion: Check,
  rechazo: X,
  eliminacion: Trash2,
  login: LogIn,
};

const TONES: Record<AuditAction, string> = {
  creacion: "text-[var(--color-success)] bg-[color-mix(in_oklab,var(--color-success)_18%,transparent)]",
  modificacion: "text-[var(--color-info)] bg-[color-mix(in_oklab,var(--color-info)_18%,transparent)]",
  aprobacion: "text-[var(--color-success)] bg-[color-mix(in_oklab,var(--color-success)_18%,transparent)]",
  rechazo: "text-[var(--color-destructive)] bg-[color-mix(in_oklab,var(--color-destructive)_18%,transparent)]",
  eliminacion: "text-[var(--color-destructive)] bg-[color-mix(in_oklab,var(--color-destructive)_18%,transparent)]",
  login: "text-[var(--color-text-muted)] bg-[var(--color-surface-2)]",
};

export const metadata: Metadata = { title: "Auditoría" };

export default function AuditPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Auditoría"
        description="Historial cronológico de eventos del portal y acciones de usuario."
        actions={<Button variant="outline">Exportar CSV</Button>}
      />

      <Card>
        <CardHeader>
          <CardTitle>Timeline de eventos</CardTitle>
          <CardDescription>
            Últimos {AUDIT_EVENTS.length} eventos registrados, ordenados de más
            reciente a más antiguo.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="flex flex-col gap-0">
            {AUDIT_EVENTS.map((event, idx) => {
              const Icon = ICONS[event.action];
              const isLast = idx === AUDIT_EVENTS.length - 1;
              return (
                <li key={event.id} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <span
                      aria-hidden
                      className={cn(
                        "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full",
                        TONES[event.action],
                      )}
                    >
                      <Icon className="h-4 w-4" />
                    </span>
                    {!isLast ? (
                      <span
                        aria-hidden
                        className="bg-[var(--color-border)] my-1 w-px flex-1"
                      />
                    ) : null}
                  </div>
                  <div className="flex flex-1 flex-col gap-1 pb-6">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-[var(--color-text-muted)]">
                        {event.id}
                      </span>
                      <Badge variant="default">
                        {AUDIT_ACTION_LABEL[event.action]}
                      </Badge>
                      <span className="tabular-nums text-xs text-[var(--color-text-muted)]">
                        {formatDateTime(event.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm font-medium">{event.resource}</p>
                    <p className="text-sm text-[var(--color-text-muted)]">
                      por <span className="font-medium">{event.user}</span> ·{" "}
                      {event.details}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}
