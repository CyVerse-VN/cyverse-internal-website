import { AccountMenu } from "@/components/account-menu";
import { DashboardView } from "@/features/dashboard/dashboard-view";
import { requireCurrentUser } from "@/lib/auth/server";

interface DashboardPageProps {
  searchParams: Promise<{ notice?: string }>;
}

export default async function DashboardPage({ searchParams }: DashboardPageProps) {
  const [user, { notice }] = await Promise.all([
    requireCurrentUser("/dashboard"),
    searchParams,
  ]);
  return <DashboardView user={user} notice={notice} accountMenu={<AccountMenu user={user} />} />;
}
