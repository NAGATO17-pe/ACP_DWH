import Link from "next/link";
import { Home, SearchX } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="bg-bg text-text flex min-h-screen items-center justify-center p-6">
      <div className="bg-surface flex w-full max-w-md flex-col items-center gap-5 rounded-lg border border-[var(--color-border)] p-8 text-center">
        <span
          aria-hidden
          className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-surface-2)] text-[var(--color-text-muted)]"
        >
          <SearchX className="h-6 w-6" />
        </span>
        <div className="flex flex-col gap-2">
          <h1 className="text-xl font-semibold">Página no encontrada</h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            La ruta que buscas no existe o no tienes permiso para acceder a
            ella.
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/">
            <Home aria-hidden className="h-4 w-4" />
            Ir al inicio
          </Link>
        </Button>
      </div>
    </main>
  );
}
