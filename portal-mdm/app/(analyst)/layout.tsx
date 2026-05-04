import { redirect } from "next/navigation";
import { Compass, FlaskConical, FileText } from "lucide-react";
import { getSession } from "@/lib/auth/session";
import { ROLE_HOME } from "@/lib/auth/rbac";
import { RoleShell } from "@/components/layout/role-shell";

const NAV = [
  { href: "/explore", label: "Exploración", icon: Compass },
  { href: "/models", label: "Modelos", icon: FlaskConical },
  { href: "/reports", label: "Reportes", icon: FileText },
];

export default async function AnalystLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();
  if (!session) redirect("/login");
  if (session.role !== "analyst") redirect(ROLE_HOME[session.role]);

  return (
    <RoleShell role="analyst" userName={session.name ?? session.email} navItems={NAV}>
      {children}
    </RoleShell>
  );
}
