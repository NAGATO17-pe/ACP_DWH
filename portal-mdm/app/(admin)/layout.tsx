import { redirect } from "next/navigation";
import { Database, GitPullRequestArrow, ShieldAlert, History } from "lucide-react";
import { getSession } from "@/lib/auth/session";
import { ROLE_HOME } from "@/lib/auth/rbac";
import { RoleShell } from "@/components/layout/role-shell";

const NAV = [
  { href: "/entities", label: "Entidades", icon: Database },
  { href: "/workflows", label: "Workflows", icon: GitPullRequestArrow },
  { href: "/quality", label: "Calidad de datos", icon: ShieldAlert },
  { href: "/audit", label: "Auditoría", icon: History },
];

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();
  if (!session) redirect("/login");
  if (session.role !== "admin") redirect(ROLE_HOME[session.role]);

  return (
    <RoleShell role="admin" userName={session.name ?? session.email} navItems={NAV}>
      {children}
    </RoleShell>
  );
}
