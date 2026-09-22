import { UserManagement } from "@/features/admin/user-management";
import { backendRequest, getAccessToken } from "@/lib/auth/server";
import { isUserListResponse } from "@/lib/auth/types";
import { redirect } from "next/navigation";

interface UsersPageProps {
  searchParams: Promise<{ page?: string; query?: string }>;
}

export default async function UsersPage({ searchParams }: UsersPageProps) {
  const [token, params] = await Promise.all([getAccessToken(), searchParams]);
  if (!token) {
    redirect("/login?next=%2Fadmin%2Fusers");
  }

  const page = Math.max(1, Number.parseInt(params.page ?? "1", 10) || 1);
  const query = (params.query ?? "").slice(0, 100);
  const search = new URLSearchParams({ page: String(page), page_size: "20" });
  if (query) search.set("query", query);

  let response: Response;
  try {
    response = await backendRequest(`/admin/users?${search}`, {}, token);
  } catch {
    return <UserServiceUnavailable />;
  }
  if (response.status === 401) {
    redirect("/login?next=%2Fadmin%2Fusers");
  }
  if (response.status === 403) {
    redirect("/dashboard?notice=admin-required");
  }
  if (!response.ok) {
    return <UserServiceUnavailable />;
  }

  const data: unknown = await response.json().catch(() => null);
  if (!isUserListResponse(data)) {
    return <UserServiceUnavailable />;
  }
  return <UserManagement data={data} currentUserId={data.current_user_id} query={query} />;
}

function UserServiceUnavailable() {
  return (
    <main className="admin-page">
      <div className="empty-state">
        <strong>User service unavailable</strong>
        <p>Please refresh the page or try again later.</p>
      </div>
    </main>
  );
}
