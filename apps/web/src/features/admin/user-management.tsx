"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useActionState, useEffect, useRef, useTransition } from "react";
import {
  KeyRound,
  Pencil,
  Search,
  UserCheck,
  UserCog,
  UserPlus,
  UserX,
  X,
} from "lucide-react";

import { SubmitButton } from "@/components/submit-button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  createUserAction,
  resetPasswordAction,
  toggleUserStatusAction,
  updateUserAction,
} from "@/features/admin/actions";
import { useLanguage } from "@/lib/i18n/context";
import type { AuthUser, UserListResponse } from "@/lib/auth/types";
import { INITIAL_ACTION_STATE } from "@/lib/auth/types";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function ActionMessage({ status, message }: { status: string; message: string }) {
  if (!message) return null;
  return (
    <p className={`form-message form-message--${status}`} role="status">
      {message}
    </p>
  );
}

function DialogHeading({
  eyebrow,
  title,
  description,
  icon: Icon,
  titleId,
  onClose,
}: {
  eyebrow: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  titleId: string;
  onClose: () => void;
}) {
  return (
    <div className="dialog__hero">
      <span className="dialog__hero-icon" aria-hidden="true">
        <Icon className="h-5 w-5 text-cyan-300" />
      </span>
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2 id={titleId}>{title}</h2>
        <p>{description}</p>
      </div>
      <button
        type="button"
        className="dialog__close hover:bg-white/20 transition-colors"
        onClick={onClose}
        aria-label="Close dialog"
      >
        <X className="h-4 w-4 m-auto" />
      </button>
    </div>
  );
}

function CreateUserDialog() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [state, action] = useActionState(createUserAction, INITIAL_ACTION_STATE);
  const { t } = useLanguage();

  useEffect(() => {
    if (state.status === "success") {
      const timer = window.setTimeout(() => dialogRef.current?.close(), 700);
      return () => window.clearTimeout(timer);
    }
  }, [state]);

  return (
    <>
      <button
        className="primary-button flex items-center gap-2"
        type="button"
        onClick={() => dialogRef.current?.showModal()}
      >
        <UserPlus className="h-4 w-4" aria-hidden="true" />
        <span>{t("admin.newUser")}</span>
      </button>
      <dialog
        className="dialog dialog--account"
        ref={dialogRef}
        aria-labelledby="create-user-title"
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            dialogRef.current?.close();
          }
        }}
      >
        <form action={action} className="admin-form">
          <DialogHeading
            eyebrow={t("admin.createEyebrow")}
            title={t("admin.createTitle")}
            description={t("admin.createDesc")}
            icon={UserPlus}
            titleId="create-user-title"
            onClose={() => dialogRef.current?.close()}
          />
          <div className="admin-form__body">
            <label className="form-field">
              <span className="field-label">
                {t("admin.username")} <b>{t("admin.required")}</b>
              </span>
              <input
                className="field-control"
                name="username"
                required
                minLength={3}
                maxLength={64}
                pattern="[A-Za-z0-9._-]+"
                autoCapitalize="none"
                autoComplete="off"
                spellCheck={false}
                placeholder="e.g. cyverse"
                aria-describedby="username-rule"
              />
              <small className="field-hint" id="username-rule">
                {t("admin.usernameHint")}
              </small>
            </label>
            <div className="form-grid">
              <label className="form-field">
                <span className="field-label">
                  {t("admin.displayName")} <b>{t("admin.required")}</b>
                </span>
                <input
                  className="field-control"
                  name="display_name"
                  required
                  maxLength={100}
                  placeholder="e.g. CyVerse"
                />
                <small className="field-hint">{t("admin.displayNameHint")}</small>
              </label>
              <label className="form-field">
                <span className="field-label">{t("admin.team")}</span>
                <input
                  className="field-control"
                  name="team"
                  maxLength={100}
                  placeholder="e.g. Data Platform"
                />
                <small className="field-hint">{t("admin.teamHint")}</small>
              </label>
            </div>
            <div className="form-grid">
              <label className="form-field">
                <span className="field-label">
                  {t("admin.role")} <b>{t("admin.required")}</b>
                </span>
                <select className="field-control" name="role" defaultValue="member">
                  <option value="member">{t("admin.member")}</option>
                  <option value="admin">{t("admin.administrator")}</option>
                </select>
                <small className="field-hint">{t("admin.roleHint")}</small>
              </label>
              <label className="form-field">
                <span className="field-label">
                  {t("admin.tempPassword")} <b>{t("admin.required")}</b>
                </span>
                <input
                  className="field-control"
                  name="password"
                  type="password"
                  required
                  minLength={8}
                  maxLength={128}
                  autoComplete="new-password"
                  placeholder="At least 8 characters"
                />
                <small className="field-hint">{t("admin.tempPasswordHint")}</small>
              </label>
            </div>
            <label className="form-field">
              <span className="field-label">{t("admin.notebooklmEmail")}</span>
              <input
                className="field-control"
                name="notebooklm_email"
                type="email"
                maxLength={320}
                placeholder="researcher@gmail.com"
              />
              <small className="field-hint">{t("admin.notebooklmHint")}</small>
            </label>
            <ActionMessage {...state} />
          </div>
          <div className="dialog__actions dialog__actions--footer">
            <button
              className="secondary-button"
              type="button"
              onClick={() => dialogRef.current?.close()}
            >
              {t("admin.cancel")}
            </button>
            <SubmitButton className="primary-button" pendingLabel={t("admin.creating")}>
              {t("admin.createUser")}
            </SubmitButton>
          </div>
        </form>
      </dialog>
    </>
  );
}

function UserActions({ user, currentUserId }: { user: AuthUser; currentUserId: string }) {
  const editRef = useRef<HTMLDialogElement>(null);
  const passwordRef = useRef<HTMLDialogElement>(null);
  const [editState, editAction] = useActionState(updateUserAction, INITIAL_ACTION_STATE);
  const [passwordState, passwordAction] = useActionState(resetPasswordAction, INITIAL_ACTION_STATE);
  const [statusState, statusAction] = useActionState(toggleUserStatusAction, INITIAL_ACTION_STATE);
  const { t } = useLanguage();
  const isSelf = user.id === currentUserId;

  useEffect(() => {
    if (editState.status === "success") {
      const timer = window.setTimeout(() => editRef.current?.close(), 700);
      return () => window.clearTimeout(timer);
    }
  }, [editState]);

  useEffect(() => {
    if (passwordState.status === "success") {
      const timer = window.setTimeout(() => passwordRef.current?.close(), 900);
      return () => window.clearTimeout(timer);
    }
  }, [passwordState]);

  return (
    <div className="table-actions flex items-center gap-1.5">
      <button
        className="table-button inline-flex items-center gap-1 hover:bg-blue-100 dark:hover:bg-blue-950/60 transition-colors"
        type="button"
        onClick={() => editRef.current?.showModal()}
      >
        <Pencil className="h-3 w-3" />
        <span>{t("admin.edit")}</span>
      </button>
      <button
        className="table-button inline-flex items-center gap-1 hover:bg-blue-100 dark:hover:bg-blue-950/60 transition-colors"
        type="button"
        onClick={() => passwordRef.current?.showModal()}
      >
        <KeyRound className="h-3 w-3" />
        <span>{t("admin.password")}</span>
      </button>
      <form
        action={statusAction}
        onSubmit={(event) => {
          const actionText = user.is_active ? t("admin.confirmDeactivate") : t("admin.confirmActivate");
          if (!window.confirm(`${actionText} ${user.username}?`)) {
            event.preventDefault();
          }
        }}
      >
        <input type="hidden" name="user_id" value={user.id} />
        <input type="hidden" name="is_active" value={String(!user.is_active)} />
        <button
          className="table-button inline-flex items-center gap-1 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
          type="submit"
          disabled={isSelf}
        >
          {user.is_active ? (
            <>
              <UserX className="h-3 w-3 text-red-500" />
              <span>{t("admin.deactivate")}</span>
            </>
          ) : (
            <>
              <UserCheck className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
              <span>{t("admin.activate")}</span>
            </>
          )}
        </button>
        {statusState.status === "error" && <span className="sr-only" role="alert">{statusState.message}</span>}
      </form>

      <dialog
        className="dialog dialog--account"
        ref={editRef}
        aria-labelledby={`edit-${user.id}`}
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            editRef.current?.close();
          }
        }}
      >
        <form action={editAction} className="admin-form">
          <input type="hidden" name="user_id" value={user.id} />
          <DialogHeading
            eyebrow={t("admin.editEyebrow")}
            title={t("admin.editTitle")}
            description={t("admin.editDesc")}
            icon={UserCog}
            titleId={`edit-${user.id}`}
            onClose={() => editRef.current?.close()}
          />
          <div className="admin-form__body">
            <div className="dialog-user-identity flex items-center gap-3 p-3 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60">
              <Avatar className="h-10 w-10">
                <AvatarFallback>{initials(user.display_name)}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <strong className="block text-sm font-semibold text-slate-800 dark:text-slate-100">{user.display_name}</strong>
                <small className="text-slate-500 dark:text-slate-400">@{user.username}</small>
              </div>
              <Badge variant={user.is_active ? "success" : "warning"}>
                {user.is_active ? t("admin.active") : t("admin.inactive")}
              </Badge>
            </div>
            <div className="form-grid">
              <label className="form-field">
                <span className="field-label">
                  {t("admin.displayName")} <b>{t("admin.required")}</b>
                </span>
                <input
                  className="field-control"
                  name="display_name"
                  required
                  maxLength={100}
                  defaultValue={user.display_name}
                  placeholder="e.g. CyVerse"
                />
                <small className="field-hint">{t("admin.displayNameHint")}</small>
              </label>
              <label className="form-field">
                <span className="field-label">{t("admin.team")}</span>
                <input
                  className="field-control"
                  name="team"
                  maxLength={100}
                  defaultValue={user.team ?? ""}
                  placeholder="e.g. Data Platform"
                />
                <small className="field-hint">{t("admin.teamHint")}</small>
              </label>
            </div>
            <label className="form-field">
              <span className="field-label">{t("admin.notebooklmEmail")}</span>
              <input
                className="field-control"
                name="notebooklm_email"
                type="email"
                maxLength={320}
                defaultValue={user.notebooklm_email ?? ""}
                placeholder="researcher@gmail.com"
              />
              <small className="field-hint">{t("admin.notebooklmHint")}</small>
            </label>
            <label className="form-field">
              <span className="field-label">
                {t("admin.role")} <b>{t("admin.required")}</b>
              </span>
              <select className="field-control" name="role" defaultValue={user.role} disabled={isSelf}>
                <option value="member">{t("admin.member")}</option>
                <option value="admin">{t("admin.administrator")}</option>
              </select>
              {isSelf && <input type="hidden" name="role" value={user.role} />}
              <small className="field-hint">
                {isSelf ? t("admin.selfRoleHint") : t("admin.roleHint")}
              </small>
            </label>
            <ActionMessage {...editState} />
          </div>
          <div className="dialog__actions dialog__actions--footer">
            <button className="secondary-button" type="button" onClick={() => editRef.current?.close()}>
              {t("admin.cancel")}
            </button>
            <SubmitButton className="primary-button" pendingLabel={t("admin.saving")}>
              {t("admin.saveChanges")}
            </SubmitButton>
          </div>
        </form>
      </dialog>

      <dialog
        className="dialog dialog--account"
        ref={passwordRef}
        aria-labelledby={`password-${user.id}`}
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            passwordRef.current?.close();
          }
        }}
      >
        <form action={passwordAction} className="admin-form">
          <input type="hidden" name="user_id" value={user.id} />
          <DialogHeading
            eyebrow={t("admin.passwordEyebrow")}
            title={t("admin.passwordTitle")}
            description={t("admin.passwordDesc")}
            icon={KeyRound}
            titleId={`password-${user.id}`}
            onClose={() => passwordRef.current?.close()}
          />
          <div className="admin-form__body">
            <div className="dialog-user-identity flex items-center gap-3 p-3 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60">
              <Avatar className="h-10 w-10">
                <AvatarFallback>{initials(user.display_name)}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <strong className="block text-sm font-semibold text-slate-800 dark:text-slate-100">{user.display_name}</strong>
                <small className="text-slate-500 dark:text-slate-400">@{user.username}</small>
              </div>
            </div>
            <label className="form-field">
              <span className="field-label">
                {t("admin.newTempPassword")} <b>{t("admin.required")}</b>
              </span>
              <input
                className="field-control"
                name="password"
                type="password"
                required
                minLength={8}
                maxLength={128}
                autoComplete="new-password"
                placeholder="At least 8 characters"
              />
              <small className="field-hint">{t("admin.newTempPasswordHint")}</small>
            </label>
            <ActionMessage {...passwordState} />
          </div>
          <div className="dialog__actions dialog__actions--footer">
            <button className="secondary-button" type="button" onClick={() => passwordRef.current?.close()}>
              {t("admin.cancel")}
            </button>
            <SubmitButton className="primary-button" pendingLabel={t("admin.updating")}>
              {t("admin.updatePassword")}
            </SubmitButton>
          </div>
        </form>
      </dialog>
    </div>
  );
}

export function UserManagement({
  data,
  currentUserId,
  query,
}: {
  data: UserListResponse;
  currentUserId: string;
  query: string;
}) {
  const router = useRouter();
  const [isSearchPending, startSearchTransition] = useTransition();
  const { t, language } = useLanguage();
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  const pageHref = (page: number) => `/admin/users?page=${page}${query ? `&query=${encodeURIComponent(query)}` : ""}`;

  function submitSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const nextQuery = String(formData.get("query") ?? "").trim().slice(0, 100);
    const nextPath = nextQuery ? `/admin/users?query=${encodeURIComponent(nextQuery)}` : "/admin/users";
    startSearchTransition(() => router.push(nextPath));
  }

  const dateFormatter = new Intl.DateTimeFormat(language === "vi" ? "vi-VN" : "en", {
    dateStyle: "medium",
    timeZone: "UTC",
  });

  return (
    <main className="admin-page">
      <header className="admin-header">
        <div>
          <p className="eyebrow eyebrow--blue">{t("admin.eyebrow")}</p>
          <h1>{t("admin.heading")}</h1>
          <p>{t("admin.subheading")}</p>
        </div>
        <CreateUserDialog />
      </header>
      <section className="admin-card">
        <form className="user-search" onSubmit={submitSearch}>
          <label className="flex items-center gap-2">
            <span className="sr-only">{t("admin.searchPlaceholder")}</span>
            <Search className="h-4 w-4 text-slate-400 shrink-0" aria-hidden="true" />
            <input
              name="query"
              defaultValue={query}
              maxLength={100}
              placeholder={t("admin.searchPlaceholder")}
            />
          </label>
          <button className="secondary-button" type="submit" disabled={isSearchPending}>
            {isSearchPending ? t("admin.searching") : t("admin.search")}
          </button>
        </form>
        {data.items.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("admin.username")}</th>
                  <th>{t("admin.team")}</th>
                  <th>{t("admin.notebooklmEmail")}</th>
                  <th>{t("admin.role")}</th>
                  <th>{t("admin.status")}</th>
                  <th>{t("admin.created")}</th>
                  <th><span className="sr-only">{t("admin.actions")}</span></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <div className="flex items-center gap-2.5">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback className="text-xs font-semibold">
                            {initials(user.display_name)}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <strong>{user.display_name}</strong>
                          <small>@{user.username}</small>
                        </div>
                      </div>
                    </td>
                    <td>{user.team ?? "—"}</td>
                    <td>{user.notebooklm_email ?? "—"}</td>
                    <td>
                      <Badge variant={user.role === "admin" ? "default" : "secondary"}>
                        {user.role === "admin" ? t("admin.administrator") : t("admin.member")}
                      </Badge>
                    </td>
                    <td>
                      <Badge variant={user.is_active ? "success" : "warning"}>
                        {user.is_active ? t("admin.active") : t("admin.inactive")}
                      </Badge>
                    </td>
                    <td>{dateFormatter.format(new Date(user.created_at))}</td>
                    <td><UserActions user={user} currentUserId={currentUserId} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>{t("admin.emptyTitle")}</strong>
            <p>{t("admin.emptyDesc")}</p>
          </div>
        )}
        <footer className="pagination">
          <span>
            {data.total} {data.total === 1 ? t("admin.userCount") : t("admin.usersCount")}
          </span>
          <div>
            <Link
              aria-disabled={data.page <= 1}
              className={data.page <= 1 ? "disabled" : ""}
              href={pageHref(Math.max(1, data.page - 1))}
            >
              {t("admin.previous")}
            </Link>
            <span>
              {language === "vi"
                ? `Trang ${data.page} / ${totalPages}`
                : `Page ${data.page} of ${totalPages}`}
            </span>
            <Link
              aria-disabled={data.page >= totalPages}
              className={data.page >= totalPages ? "disabled" : ""}
              href={pageHref(Math.min(totalPages, data.page + 1))}
            >
              {t("admin.next")}
            </Link>
          </div>
        </footer>
      </section>
    </main>
  );
}
