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
import { ThreadsSessionSettings } from "@/features/account/threads-session-settings";
import { useLanguage } from "@/lib/i18n/context";
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
  const { t } = useLanguage();

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
          <p className="eyebrow eyebrow--blue">{t("settings.eyebrow")}</p>
          <h1>{t("settings.heading")}</h1>
          <p>{t("settings.subheading")}</p>
        </div>
      </header>

      <div className="settings-grid">
        <aside className="settings-summary">
          <Avatar className="mx-auto h-20 w-20 ring-4 ring-blue-500/20 shadow-lg">
            <AvatarFallback className="text-xl font-bold bg-gradient-to-tr from-blue-600 to-cyan-500 text-white">
              {initials}
            </AvatarFallback>
          </Avatar>
          <h2>{user.display_name}</h2>
          <p>@{user.username}</p>
          <dl>
            <div>
              <dt>{t("settings.role")}</dt>
              <dd>
                <Badge variant={user.role === "admin" ? "default" : "secondary"}>
                  {user.role === "admin" ? t("account.adminRole") : t("account.memberRole")}
                </Badge>
              </dd>
            </div>
            <div>
              <dt>{t("settings.team")}</dt>
              <dd>{user.team ?? t("settings.notAssigned")}</dd>
            </div>
            <div>
              <dt>{t("settings.status")}</dt>
              <dd>
                <Badge variant="success">{t("settings.active")}</Badge>
              </dd>
            </div>
          </dl>
        </aside>

        <div className="settings-sections">
          <section className="settings-card">
            <div className="settings-card__heading flex items-center gap-3">
              <span className="settings-card__icon flex items-center justify-center rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400" aria-hidden="true">
                <User className="h-5 w-5" />
              </span>
              <div>
                <h2>{t("settings.profileHeading")}</h2>
                <p>{t("settings.profileSubheading")}</p>
              </div>
            </div>
            <form action={profileAction} className="settings-form">
              <label className="form-field">
                <span className="field-label">{t("settings.username")}</span>
                <input className="field-control" value={user.username} disabled />
                <small className="field-hint">{t("settings.usernameHint")}</small>
              </label>
              <label className="form-field">
                <span className="field-label">{t("settings.displayName")}</span>
                <input className="field-control" name="display_name" defaultValue={user.display_name} required maxLength={100} placeholder={t("settings.displayNamePlaceholder")} />
                <small className="field-hint">{t("settings.displayNameHint")}</small>
              </label>
              <label className="form-field">
                <span className="field-label">{t("settings.team")}</span>
                <input className="field-control" name="team" defaultValue={user.team ?? ""} maxLength={100} placeholder={t("settings.teamPlaceholder")} />
                <small className="field-hint">{t("settings.teamHint")}</small>
              </label>
              <label className="form-field">
                <span className="field-label">{t("settings.notebooklmEmail")}</span>
                <input className="field-control" name="notebooklm_email" type="email" defaultValue={user.notebooklm_email ?? ""} maxLength={320} placeholder="you@gmail.com" />
                <small className="field-hint">{t("settings.notebooklmHint")}</small>
              </label>
              <ActionMessage {...profileState} />
              <div className="settings-form__actions">
                <SubmitButton className="primary-button" pendingLabel={t("settings.saving")}>{t("settings.saveProfile")}</SubmitButton>
              </div>
            </form>
          </section>

          <section className="settings-card">
            <div className="settings-card__heading flex items-center gap-3">
              <span className="settings-card__icon settings-card__icon--security flex items-center justify-center rounded-xl bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400" aria-hidden="true">
                <ShieldCheck className="h-5 w-5" />
              </span>
              <div>
                <h2>{t("settings.securityHeading")}</h2>
                <p>{t("settings.securitySubheading")}</p>
              </div>
            </div>
            <form action={passwordAction} className="settings-form">
              <label className="form-field">
                <span className="field-label">{t("settings.currentPassword")}</span>
                <input className="field-control" name="current_password" type="password" required minLength={8} maxLength={128} autoComplete="current-password" placeholder={t("settings.currentPasswordPlaceholder")} />
              </label>
              <div className="form-grid">
                <label className="form-field">
                  <span className="field-label">{t("settings.newPassword")}</span>
                  <input className="field-control" name="new_password" type="password" required minLength={8} maxLength={128} autoComplete="new-password" placeholder={t("settings.newPasswordPlaceholder")} />
                </label>
                <label className="form-field">
                  <span className="field-label">{t("settings.confirmPassword")}</span>
                  <input className="field-control" name="confirm_password" type="password" required minLength={8} maxLength={128} autoComplete="new-password" placeholder={t("settings.confirmPasswordPlaceholder")} />
                </label>
              </div>
              <small className="field-hint">{t("settings.passwordHint")}</small>
              <ActionMessage {...passwordState} />
              <div className="settings-form__actions">
                <SubmitButton className="primary-button" pendingLabel={t("settings.updating")}>{t("settings.updatePassword")}</SubmitButton>
              </div>
            </form>
          </section>

          {user.role === "admin" && <ThreadsSessionSettings />}
        </div>
      </div>
    </main>
  );
}
