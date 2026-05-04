import type { LucideIcon } from "lucide-react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: string | number;
  unit?: string;
  delta?: number;
  deltaLabel?: string;
  icon?: LucideIcon;
  tone?: "default" | "success" | "warning" | "destructive";
}

const TONES: Record<NonNullable<KpiCardProps["tone"]>, string> = {
  default: "text-[var(--color-primary)]",
  success: "text-[var(--color-success)]",
  warning: "text-[var(--color-warning)]",
  destructive: "text-[var(--color-destructive)]",
};

export function KpiCard({
  label,
  value,
  unit,
  delta,
  deltaLabel,
  icon: Icon,
  tone = "default",
}: KpiCardProps) {
  const positive = (delta ?? 0) >= 0;

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-5">
        <div className="flex items-start justify-between">
          <span className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
            {label}
          </span>
          {Icon ? (
            <span
              aria-hidden
              className={cn(
                "bg-[var(--color-surface-2)] inline-flex h-8 w-8 items-center justify-center rounded-md",
                TONES[tone],
              )}
            >
              <Icon className="h-4 w-4" />
            </span>
          ) : null}
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="tabular-nums text-3xl font-bold">{value}</span>
          {unit ? (
            <span className="text-sm text-[var(--color-text-muted)]">
              {unit}
            </span>
          ) : null}
        </div>
        {delta !== undefined ? (
          <div
            className={cn(
              "flex items-center gap-1 text-xs",
              positive
                ? "text-[var(--color-success)]"
                : "text-[var(--color-destructive)]",
            )}
          >
            {positive ? (
              <ArrowUp aria-hidden className="h-3 w-3" />
            ) : (
              <ArrowDown aria-hidden className="h-3 w-3" />
            )}
            <span className="tabular-nums font-medium">
              {positive ? "+" : ""}
              {delta}%
            </span>
            {deltaLabel ? (
              <span className="text-[var(--color-text-muted)]">
                {deltaLabel}
              </span>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
