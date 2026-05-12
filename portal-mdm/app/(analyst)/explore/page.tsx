import type { Metadata } from "next";
import { Compass, Database, FileText, FlaskConical } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/page-header";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { KpiCard } from "@/components/charts/kpi-card";

const SHORTCUTS = [
  {
    href: "/models",
    title: "Modelos predictivos",
    description: "Explora métricas, importancia de variables y predicciones.",
    icon: FlaskConical,
  },
  {
    href: "/reports",
    title: "Reportes",
    description: "Genera reportes PDF/Excel desde plantillas predefinidas.",
    icon: FileText,
  },
];

export const metadata: Metadata = { title: "Exploración de datos" };

export default function ExplorePage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Exploración de datos"
        description="Punto de entrada para análisis y descubrimiento sobre el data warehouse."
      />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard label="Datasets disponibles" value={28} icon={Database} />
        <KpiCard
          label="Modelos en producción"
          value={3}
          delta={50}
          deltaLabel="vs. trimestre"
          icon={FlaskConical}
          tone="success"
        />
        <KpiCard
          label="Consultas (últimos 7 días)"
          value="1,284"
          delta={12}
          deltaLabel="vs. semana"
          icon={Compass}
        />
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {SHORTCUTS.map((s) => {
          const Icon = s.icon;
          return (
            <Link
              key={s.href}
              href={s.href}
              className="block focus-visible:outline-none"
            >
              <Card className="hover:border-[var(--color-primary)] transition-colors">
                <CardHeader>
                  <div className="flex items-start gap-3">
                    <span
                      aria-hidden
                      className="bg-[var(--color-surface-2)] text-[var(--color-primary)] inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md"
                    >
                      <Icon className="h-5 w-5" />
                    </span>
                    <div className="flex flex-col gap-1">
                      <CardTitle>{s.title}</CardTitle>
                      <CardDescription>{s.description}</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="text-xs text-[var(--color-text-muted)]">
                  Acceso rápido →
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
