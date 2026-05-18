import { TableSkeleton } from "@/components/ui/skeleton";

export default function EntitiesLoading() {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <div className="bg-[var(--color-surface-2)] animate-pulse h-7 w-48 rounded-md" />
        <div className="bg-[var(--color-surface-2)] animate-pulse h-4 w-80 rounded-md" />
      </div>
      <TableSkeleton rows={10} />
    </div>
  );
}
