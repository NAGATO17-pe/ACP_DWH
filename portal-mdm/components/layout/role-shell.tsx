"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import { LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Role } from "@/lib/auth/rbac";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

interface RoleShellProps {
  role: Role;
  userName?: string;
  navItems: NavItem[];
  children: React.ReactNode;
}

const ROLE_LABELS: Record<Role, string> = {
  analyst: "Analista",
  admin: "Administrador MDM",
  executive: "Ejecutivo",
};

export function RoleShell({ role, userName, navItems, children }: RoleShellProps) {
  const pathname = usePathname();

  return (
    <div className="bg-bg text-text grid min-h-screen grid-cols-1 lg:grid-cols-[260px_1fr]">
      <aside
        className="bg-surface hidden border-r border-[var(--color-border)] lg:flex lg:flex-col"
        aria-label={`Navegación — ${ROLE_LABELS[role]}`}
      >
        <div className="flex h-14 items-center gap-2 border-b border-[var(--color-border)] px-5">
          <span
            aria-hidden
            className="bg-[var(--color-primary)] inline-block h-2.5 w-2.5 rounded-full"
          />
          <span className="text-sm font-semibold tracking-tight">Portal MDM</span>
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 p-3" aria-label="Principal">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex min-h-[44px] items-center gap-3 rounded-md px-3 py-2 text-sm transition",
                  active
                    ? "bg-[var(--color-surface-2)] text-[var(--color-text)] font-medium"
                    : "text-[var(--color-text-muted)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)]",
                )}
              >
                <Icon aria-hidden className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <footer className="border-t border-[var(--color-border)] p-3 text-xs text-[var(--color-text-muted)]">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate font-medium text-[var(--color-text)]">
                {userName ?? "Sesión"}
              </p>
              <p className="truncate">{ROLE_LABELS[role]}</p>
            </div>
            <form action="/api/auth/logout" method="post">
              <button
                type="submit"
                className="hover:bg-[var(--color-surface-2)] inline-flex h-11 w-11 items-center justify-center rounded-md transition"
                aria-label="Cerrar sesión"
              >
                <LogOut aria-hidden className="h-4 w-4" />
              </button>
            </form>
          </div>
        </footer>
      </aside>

      <main id="main-content" className="flex min-h-screen flex-col" tabIndex={-1}>
        <header className="bg-surface flex h-14 items-center justify-between border-b border-[var(--color-border)] px-6">
          <span className="text-sm font-medium text-[var(--color-text-muted)]">
            {ROLE_LABELS[role]}
          </span>
          <span className="text-xs text-[var(--color-text-muted)]">
            {userName}
          </span>
        </header>
        <div className="flex-1 p-6">{children}</div>
      </main>
    </div>
  );
}
