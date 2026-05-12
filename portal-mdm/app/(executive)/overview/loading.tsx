import { KpiSkeleton, ChartSkeleton } from "@/components/ui/skeleton";

export default function OverviewLoading() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <div className="bg-[var(--color-surface-2)] animate-pulse h-7 w-48 rounded-md" />
        <div className="bg-[var(--color-surface-2)] animate-pulse h-4 w-72 rounded-md" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => <KpiSkeleton key={i} />)}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="bg-surface rounded-lg border border-[var(--color-border)] p-5 lg:col-span-2">
          <ChartSkeleton height={300} />
        </div>
        <div className="bg-surface rounded-lg border border-[var(--color-border)] p-5">
          <ChartSkeleton height={300} />
        </div>
      </div>
    </div>
  );
}
