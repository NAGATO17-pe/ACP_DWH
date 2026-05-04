import { Construction } from "lucide-react";

interface Props {
  title: string;
  description: string;
  sprint: string;
}

export function PagePlaceholder({ title, description, sprint }: Props) {
  return (
    <section className="bg-surface flex flex-col gap-3 rounded-lg border border-[var(--color-border)] p-8">
      <header className="flex items-start gap-3">
        <span
          aria-hidden
          className="bg-[var(--color-surface-2)] inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md"
        >
          <Construction className="h-5 w-5 text-[var(--color-warning)]" />
        </span>
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="text-sm text-[var(--color-text-muted)]">{description}</p>
        </div>
      </header>
      <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
        Pendiente · {sprint}
      </p>
    </section>
  );
}
