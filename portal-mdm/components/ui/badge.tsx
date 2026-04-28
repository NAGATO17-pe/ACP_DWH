import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--color-surface-2)] text-[var(--color-text)] border-[var(--color-border)]",
        success:
          "bg-[color-mix(in_oklab,var(--color-success)_18%,transparent)] text-[var(--color-success)] border-[color-mix(in_oklab,var(--color-success)_30%,transparent)]",
        warning:
          "bg-[color-mix(in_oklab,var(--color-warning)_18%,transparent)] text-[var(--color-warning)] border-[color-mix(in_oklab,var(--color-warning)_30%,transparent)]",
        destructive:
          "bg-[color-mix(in_oklab,var(--color-destructive)_18%,transparent)] text-[var(--color-destructive)] border-[color-mix(in_oklab,var(--color-destructive)_30%,transparent)]",
        info: "bg-[color-mix(in_oklab,var(--color-info)_18%,transparent)] text-[var(--color-info)] border-[color-mix(in_oklab,var(--color-info)_30%,transparent)]",
        primary:
          "bg-[color-mix(in_oklab,var(--color-primary)_18%,transparent)] text-[var(--color-primary)] border-[color-mix(in_oklab,var(--color-primary)_30%,transparent)]",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
