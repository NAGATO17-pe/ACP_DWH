import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "bg-surface h-10 w-full rounded-md border border-[var(--color-border)] px-3 text-sm transition placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-primary)] focus:outline-none disabled:opacity-60",
      className,
    )}
    {...props}
  />
));
Input.displayName = "Input";
