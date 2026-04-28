import { redirect } from "next/navigation";
import { LayoutDashboard } from "lucide-react";
import { getSession } from "@/lib/auth/session";
import { ROLE_HOME } from "@/lib/auth/rbac";
import { RoleShell } from "@/components/layout/role-shell";

const NAV = [{ href: "/overview", label: "Overview", icon: LayoutDashboard }];

export default async function ExecutiveLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();
  if (!session) redirect("/login");
  if (session.role !== "executive") redirect(ROLE_HOME[session.role]);

  return (
    <RoleShell role="executive" userName={session.name ?? session.email} navItems={NAV}>
      {children}
    </RoleShell>
  );
}
