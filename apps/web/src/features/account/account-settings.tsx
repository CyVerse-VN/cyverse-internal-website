"use client";

import { useActionState } from "react";
import { ShieldCheck, User } from "lucide-react";

import { SubmitButton } from "@/components/submit-button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  changePasswordAction,
  updateProfileAction,
} from "@/features/account/actions";
import type { AuthUser } from "@/lib/auth/types";
import { INITIAL_ACTION_STATE } from "@/lib/auth/types";

function ActionMessage({ status, message }: { status: string; message: string }) {
  if (!message) return null;
  return <p className={`form-message form-message--${status}`} role="status">{message}</p>;
}

export function AccountSettings({ user }: { user: AuthUser }) {
  const [profileState, profileAction] = useActionState(
    updateProfileAction,
    INITIAL_ACTION_STATE,
  );
  const [passwordState, passwordAction] = useActionState(
    changePasswordAction,
    INITIAL_ACTION_STATE,
  );

  const initials = user.display_name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <main className="settings-page">
      <header className="settings-header">
        <div>
          <p className="eyebrow eyebrow--blue">Personal workspace</p>
          <h1>Account Settings</h1>
          <p>Manage your personal details and keep your account secure.</p>
        </div>
      </header>

      <div className="settings-grid">
        <aside className="settings-summary">
          <Avatar className="mx-auto h-20 w-20 ring-4 ring-blue-500/20 shadow-lg">
            <AvatarFallback className="text-xl font-bold bg-gradient-to-tr from-blue-600 to-cyan-500">
              {initials}
            </AvatarFallback>
          </Avatar>
          <h2>{user.display_name}</h2>
          <p>@{user.username}</p>
          <dl>
            <div>
              <dt>Role</dt>
              <dd>
                <Badge variant={user.role === "admin" ? "default" : "secondary"}>
                  {user.role === "admin" ? "Administrator" : "Member"}
                </Badge>
              </dd>
            </div>
            <div>
              <dt>Team</dt>
              <dd>{user.team ?? "Not assigned"}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>
                <Badge variant="success">Active</Badge>
              </dd>
            </div>
          </dl>
        </aside>

        <div className="settings-sections">
          <section className="settings-card">
            <div className="settings-card__heading flex items-center gap-3">
              <span className="settings-card__icon flex items-center justify-center rounded-xl bg-blue-50 text-blue-600" aria-hidden="true">
                <User className="h-5 w-5" />
              </span>
              <div>
                <h2>Profile details</h2>
                <p>This information appears across your workspace.</p>
              </div>
            </div>
            <form action={profileAction} className="settings-form">
              <label className="form-field">
                <span className="field-label">Username</span>
                <input className="field-control" value={user.username} disabled />
                <small className="field-hint">Usernames are permanent and managed by an administrator.</small>
              </label>
              <label className="form-field">
                <span className="field-label">Display name</span>
                <input className="field-control" name="display_name" defaultValue={user.display_name} required maxLength={100} placeholder="e.g. CyVerse" />
                <small className="field-hint">Use the name teammates will recognize.</small>
              </label>
              <label className="form-field">
                <span className="field-label">Team</span>
                <input className="field-control" name="team" defaultValue={user.team ?? ""} maxLength={100} placeholder="e.g. Data Platform" />
                <small className="field-hint">Optional. Helps teammates understand where you work.</small>
              </label>
              <ActionMessage {...profileState} />
              <div className="settings-form__actions">
                <SubmitButton className="primary-button" pendingLabel="Saving…">Save profile</SubmitButton>
              </div>
            </form>
          </section>

          <section className="settings-card">
            <div className="settings-card__heading flex items-center gap-3">
              <span className="settings-card__icon settings-card__icon--security flex items-center justify-center rounded-xl bg-purple-50 text-purple-600" aria-hidden="true">
                <ShieldCheck className="h-5 w-5" />
              </span>
              <div>
                <h2>Password & security</h2>
                <p>Changing your password signs out every other session.</p>
              </div>
            </div>
            <form action={passwordAction} className="settings-form">
              <label className="form-field">
                <span className="field-label">Current password</span>
                <input className="field-control" name="current_password" type="password" required minLength={8} maxLength={128} autoComplete="current-password" placeholder="Enter your current password" />
              </label>
              <div className="form-grid">
                <label className="form-field">
                  <span className="field-label">New password</span>
                  <input className="field-control" name="new_password" type="password" required minLength={8} maxLength={128} autoComplete="new-password" placeholder="At least 8 characters" />
                </label>
                <label className="form-field">
                  <span className="field-label">Confirm password</span>
                  <input className="field-control" name="confirm_password" type="password" required minLength={8} maxLength={128} autoComplete="new-password" placeholder="Repeat the new password" />
                </label>
              </div>
              <small className="field-hint">Use 8–128 characters and avoid reusing your current password.</small>
              <ActionMessage {...passwordState} />
              <div className="settings-form__actions">
                <SubmitButton className="primary-button" pendingLabel="Updating…">Update password</SubmitButton>
              </div>
            </form>
          </section>
        </div>
      </div>
    </main>
  );
}

