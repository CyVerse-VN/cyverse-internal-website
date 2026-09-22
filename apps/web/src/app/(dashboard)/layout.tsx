import { DashboardShell } from "@/features/dashboard/dashboard-shell";
import { requireCurrentUser } from "@/lib/auth/server";

export const dynamic = "force-dynamic";

export default async function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const user = await requireCurrentUser("/dashboard");
  return <DashboardShell user={user}>{children}</DashboardShell>;
}
