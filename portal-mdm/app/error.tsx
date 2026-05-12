"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function GlobalError({
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
    <main className="bg-bg text-text flex min-h-screen items-center justify-center p-6">
      <div className="bg-surface flex w-full max-w-md flex-col items-center gap-5 rounded-lg border border-[var(--color-border)] p-8 text-center">
        <span
          aria-hidden
          className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[color-mix(in_oklab,var(--color-destructive)_18%,transparent)] text-[var(--color-destructive)]"
        >
          <AlertTriangle className="h-6 w-6" />
        </span>
        <div className="flex flex-col gap-2">
          <h1 className="text-xl font-semibold">Algo salió mal</h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Ocurrió un error inesperado. Puedes intentarlo de nuevo o contactar
            soporte si el problema persiste.
          </p>
          {error.digest ? (
            <p className="font-mono text-xs text-[var(--color-text-muted)]">
              Ref: {error.digest}
            </p>
          ) : null}
        </div>
        <Button onClick={unstable_retry} variant="outline">
          <RefreshCw aria-hidden className="h-4 w-4" />
          Intentar de nuevo
        </Button>
      </div>
    </main>
  );
}
