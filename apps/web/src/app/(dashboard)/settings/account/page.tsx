import { AccountSettings } from "@/features/account/account-settings";
import { requireCurrentUser } from "@/lib/auth/server";

export default async function AccountSettingsPage() {
  const user = await requireCurrentUser("/settings/account");
  return <AccountSettings user={user} />;
}
