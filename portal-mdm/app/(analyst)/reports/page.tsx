import type { Metadata } from "next";
import { Download, FileText } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const REPORTS = [
  {
    id: "RPT-001",
    title: "Reporte mensual de calidad MDM",
    description: "PDF con KPIs de completitud, validez y errores activos.",
    formats: ["PDF", "Excel"],
  },
  {
    id: "RPT-002",
    title: "Performance de modelos predictivos",
    description: "Métricas comparadas (AUC, F1) entre modelos en producción.",
    formats: ["PDF"],
  },
  {
    id: "RPT-003",
    title: "Top 100 entidades con más cambios",
    description: "Listado priorizado para revisión del equipo de gobierno.",
    formats: ["Excel"],
  },
  {
    id: "RPT-004",
    title: "Auditoría de aprobaciones",
    description: "Detalle de workflows aprobados / rechazados por usuario.",
    formats: ["PDF", "Excel"],
  },
];

export const metadata: Metadata = { title: "Reportes" };

export default function ReportsPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Reportes"
        description="Plantillas pre-configuradas para análisis ejecutivo y auditoría."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {REPORTS.map((r) => (
          <Card key={r.id}>
            <CardHeader>
              <div className="flex items-start gap-3">
                <span
                  aria-hidden
                  className="bg-[var(--color-surface-2)] text-[var(--color-primary)] inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md"
                >
                  <FileText className="h-5 w-5" />
                </span>
                <div className="flex flex-col gap-1">
                  <CardTitle>{r.title}</CardTitle>
                  <CardDescription>{r.description}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex items-center justify-between">
              <span className="text-xs text-[var(--color-text-muted)]">
                Formatos: {r.formats.join(" · ")}
              </span>
              <Button variant="outline" size="sm">
                <Download aria-hidden className="h-4 w-4" />
                Descargar
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
