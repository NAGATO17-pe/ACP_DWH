"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function SegmentError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div
      role="alert"
      className="bg-surface flex flex-col items-center gap-4 rounded-lg border border-[var(--color-destructive)]/40 p-8 text-center"
    >
      <AlertTriangle aria-hidden className="h-8 w-8 text-[var(--color-destructive)]" />
      <div className="flex flex-col gap-1">
        <p className="font-semibold">Error al cargar esta sección</p>
        <p className="text-sm text-[var(--color-text-muted)]">
          Puedes reintentarlo sin perder el resto del portal.
        </p>
      </div>
      <Button onClick={unstable_retry} variant="outline" size="sm">
        <RefreshCw aria-hidden className="h-4 w-4" />
        Reintentar
      </Button>
    </div>
  );
}
