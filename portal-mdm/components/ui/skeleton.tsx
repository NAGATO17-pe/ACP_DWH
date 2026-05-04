import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "bg-[var(--color-surface-2)] animate-pulse rounded-md",
        className,
      )}
    />
  );
}

export function KpiSkeleton() {
  return (
    <div className="bg-surface rounded-lg border border-[var(--color-border)] p-5">
      <div className="flex flex-col gap-3">
        <div className="flex items-start justify-between">
          <Skeleton className="h-3 w-28" />
          <Skeleton className="h-8 w-8 rounded-md" />
        </div>
        <Skeleton className="h-9 w-20" />
        <Skeleton className="h-3 w-24" />
      </div>
    </div>
  );
}

export function TableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="bg-surface overflow-hidden rounded-lg border border-[var(--color-border)]">
      <div className="bg-[var(--color-surface-2)] border-b border-[var(--color-border)] px-4 py-3">
        <Skeleton className="h-3 w-48" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 border-b border-[var(--color-border)] px-4 py-3"
        >
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-40 flex-1" />
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-3 w-16" />
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton({ height = 260 }: { height?: number }) {
  return (
    <div
      role="status"
      aria-label="Cargando gráfico"
      className="bg-[var(--color-surface-2)] flex animate-pulse items-center justify-center rounded-md"
      style={{ height }}
    >
      <span className="sr-only">Cargando gráfico…</span>
    </div>
  );
}
