import { redirect } from "next/navigation";
import { Suspense } from "react";
import { getSession } from "@/lib/auth/session";
import { ROLE_HOME } from "@/lib/auth/rbac";
import { LoginForm } from "./login-form";

export const metadata = {
  title: "Iniciar sesión — Portal MDM",
};

export default async function LoginPage() {
  const session = await getSession();
  if (session) redirect(ROLE_HOME[session.role]);

  return (
    <main className="bg-bg flex min-h-screen items-center justify-center p-6">
      <div className="bg-surface w-full max-w-md rounded-lg border border-[var(--color-border)] p-8 shadow-2xl">
        <Suspense>
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
