"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { loginSchema, type LoginInput } from "@/lib/schemas/auth";
import { ROLE_HOME, isValidRole } from "@/lib/auth/rbac";

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") ?? null;
  const [serverError, setServerError] = useState<string | null>(null);

  const form = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    mode: "onBlur",
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    setServerError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(values),
      });

      if (!res.ok) {
        const data = (await res.json().catch(() => ({}))) as { detail?: string };
        setServerError(data.detail ?? "No se pudo iniciar sesión");
        return;
      }

      const meRes = await fetch("/api/auth/me", { cache: "no-store" }).catch(
        () => null,
      );
      let target = next ?? "/";
      if (meRes?.ok) {
        const me = (await meRes.json().catch(() => null)) as
          | { role?: unknown }
          | null;
        if (me && isValidRole(me.role) && !next) target = ROLE_HOME[me.role];
      }
      router.replace(target);
      router.refresh();
    } catch {
      setServerError("Error de red. Reintenta en unos segundos.");
    }
  });

  const fieldErrors = form.formState.errors;
  const submitting = form.formState.isSubmitting;

  return (
    <form
      noValidate
      onSubmit={onSubmit}
      className="flex w-full max-w-sm flex-col gap-5"
      aria-describedby={serverError ? "login-error" : undefined}
    >
      <header className="flex flex-col gap-2">
        <span className="bg-surface text-primary-foreground inline-flex h-10 w-10 items-center justify-center rounded-md border border-[var(--color-border)]">
          <ShieldCheck aria-hidden className="h-5 w-5 text-[var(--color-primary)]" />
        </span>
        <h1 className="text-2xl font-semibold tracking-tight">Portal MDM</h1>
        <p className="text-sm text-[var(--color-text-muted)]">
          Acceso para analistas, administradores MDM y ejecutivos.
        </p>
      </header>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="email" className="text-sm font-medium">
          Correo corporativo
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          inputMode="email"
          aria-invalid={Boolean(fieldErrors.email)}
          aria-describedby={fieldErrors.email ? "email-error" : undefined}
          className="bg-surface border-[var(--color-border)] focus:border-[var(--color-primary)] h-11 rounded-md border px-3 text-sm outline-none transition placeholder:text-[var(--color-text-muted)]"
          placeholder="usuario@empresa.com"
          {...form.register("email")}
        />
        {fieldErrors.email ? (
          <p id="email-error" role="alert" className="text-xs text-[var(--color-destructive)]">
            {fieldErrors.email.message}
          </p>
        ) : null}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="password" className="text-sm font-medium">
          Contraseña
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          aria-invalid={Boolean(fieldErrors.password)}
          aria-describedby={fieldErrors.password ? "password-error" : undefined}
          className="bg-surface border-[var(--color-border)] focus:border-[var(--color-primary)] h-11 rounded-md border px-3 text-sm outline-none transition placeholder:text-[var(--color-text-muted)]"
          placeholder="••••••••"
          {...form.register("password")}
        />
        {fieldErrors.password ? (
          <p id="password-error" role="alert" className="text-xs text-[var(--color-destructive)]">
            {fieldErrors.password.message}
          </p>
        ) : null}
      </div>

      {serverError ? (
        <p
          id="login-error"
          role="alert"
          className="rounded-md border border-[var(--color-destructive)]/40 bg-[var(--color-destructive)]/10 px-3 py-2 text-sm text-[var(--color-destructive)]"
        >
          {serverError}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={submitting}
        className="bg-[var(--color-primary)] text-[var(--color-primary-foreground)] inline-flex h-11 items-center justify-center gap-2 rounded-md text-sm font-medium transition hover:bg-[var(--color-primary-2)] disabled:opacity-60"
      >
        {submitting ? (
          <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
        ) : null}
        Iniciar sesión
      </button>
    </form>
  );
}
