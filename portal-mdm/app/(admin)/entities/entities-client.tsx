"use client";

import * as React from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table/data-table";
import {
  ENTITY_TYPE_LABEL,
  type EntityStatus,
  type EntityType,
  type MdmEntity,
} from "@/lib/mock/entities";
import { formatDate, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

const STATUS_VARIANT: Record<
  EntityStatus,
  "success" | "warning" | "destructive" | "default"
> = {
  validado: "success",
  pendiente: "warning",
  rechazado: "destructive",
  borrador: "default",
};

const TABS: Array<{ value: EntityType | "all"; label: string }> = [
  { value: "all", label: "Todas" },
  { value: "cliente", label: ENTITY_TYPE_LABEL.cliente },
  { value: "producto", label: ENTITY_TYPE_LABEL.producto },
  { value: "proveedor", label: ENTITY_TYPE_LABEL.proveedor },
  { value: "ubicacion", label: ENTITY_TYPE_LABEL.ubicacion },
];

const COLUMNS: ColumnDef<MdmEntity>[] = [
  {
    accessorKey: "code",
    header: "Código",
    cell: ({ row }) => (
      <span className="font-mono text-xs text-[var(--color-text-muted)]">
        {row.original.code}
      </span>
    ),
  },
  {
    accessorKey: "name",
    header: "Nombre",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.name}</span>
    ),
  },
  {
    accessorKey: "type",
    header: "Tipo",
    cell: ({ row }) => (
      <span className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
        {ENTITY_TYPE_LABEL[row.original.type]}
      </span>
    ),
  },
  {
    accessorKey: "status",
    header: "Estado",
    cell: ({ row }) => (
      <Badge variant={STATUS_VARIANT[row.original.status]}>
        {row.original.status}
      </Badge>
    ),
  },
  {
    accessorKey: "completeness",
    header: "Completitud",
    cell: ({ row }) => {
      const v = row.original.completeness;
      const tone =
        v >= 90 ? "success" : v >= 80 ? "warning" : "destructive";
      return (
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "tabular-nums w-12 text-right text-xs font-semibold",
              tone === "success" && "text-[var(--color-success)]",
              tone === "warning" && "text-[var(--color-warning)]",
              tone === "destructive" && "text-[var(--color-destructive)]",
            )}
          >
            {formatPercent(v, 0)}
          </span>
          <div className="bg-[var(--color-surface-2)] h-1.5 w-24 overflow-hidden rounded-full">
            <div
              className={cn(
                "h-full",
                tone === "success" && "bg-[var(--color-success)]",
                tone === "warning" && "bg-[var(--color-warning)]",
                tone === "destructive" && "bg-[var(--color-destructive)]",
              )}
              style={{ width: `${v}%` }}
            />
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: "owner",
    header: "Responsable",
  },
  {
    accessorKey: "updatedAt",
    header: "Actualizado",
    cell: ({ row }) => (
      <span className="tabular-nums text-xs text-[var(--color-text-muted)]">
        {formatDate(row.original.updatedAt)}
      </span>
    ),
  },
];

export function EntitiesClient({ data }: { data: MdmEntity[] }) {
  const [active, setActive] = React.useState<EntityType | "all">("all");

  const filtered = React.useMemo(() => {
    if (active === "all") return data;
    return data.filter((e) => e.type === active);
  }, [active, data]);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div
          role="tablist"
          aria-label="Filtro por tipo de entidad"
          className="bg-surface inline-flex h-10 items-center gap-1 rounded-md border border-[var(--color-border)] p-1"
        >
          {TABS.map((tab) => (
            <button
              key={tab.value}
              type="button"
              role="tab"
              aria-selected={active === tab.value}
              onClick={() => setActive(tab.value)}
              className={cn(
                "h-8 rounded-md px-3 text-sm font-medium transition",
                active === tab.value
                  ? "bg-[var(--color-surface-2)] text-[var(--color-text)]"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]",
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <Button>
          <Plus aria-hidden className="h-4 w-4" />
          Nueva entidad
        </Button>
      </div>

      <DataTable
        columns={COLUMNS}
        data={filtered}
        searchPlaceholder="Buscar por nombre, código u responsable…"
        emptyMessage="No hay entidades para los filtros aplicados."
      />
    </div>
  );
}
