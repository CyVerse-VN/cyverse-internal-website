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
import type { AuthUser, UserListResponse } from "@/lib/auth/types";
import { INITIAL_ACTION_STATE } from "@/lib/auth/types";

const userDateFormatter = new Intl.DateTimeFormat("en", {
  dateStyle: "medium",
  timeZone: "UTC",
});

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
        <span>New User</span>
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
            eyebrow="Account provisioning"
            title="Create user"
            description="Set up a secure workspace account and assign its initial access level."
            icon={UserPlus}
            titleId="create-user-title"
            onClose={() => dialogRef.current?.close()}
          />
          <div className="admin-form__body">
            <label className="form-field">
              <span className="field-label">Username <b>Required</b></span>
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
                3–64 characters, no spaces. Use letters, numbers, dots, underscores, or hyphens.
              </small>
            </label>
            <div className="form-grid">
              <label className="form-field">
                <span className="field-label">Display name <b>Required</b></span>
                <input className="field-control" name="display_name" required maxLength={100} placeholder="e.g. CyVerse" />
                <small className="field-hint">The name shown to teammates.</small>
              </label>
              <label className="form-field">
                <span className="field-label">Team</span>
                <input className="field-control" name="team" maxLength={100} placeholder="e.g. Data Platform" />
                <small className="field-hint">Optional organizational group.</small>
              </label>
            </div>
            <div className="form-grid">
              <label className="form-field">
                <span className="field-label">Role <b>Required</b></span>
                <select className="field-control" name="role" defaultValue="member">
                  <option value="member">Member</option>
                  <option value="admin">Administrator</option>
                </select>
                <small className="field-hint">Administrators can manage all accounts.</small>
              </label>
              <label className="form-field">
                <span className="field-label">Temporary password <b>Required</b></span>
                <input className="field-control" name="password" type="password" required minLength={8} maxLength={128} autoComplete="new-password" placeholder="At least 8 characters" />
                <small className="field-hint">Use 8–128 characters.</small>
              </label>
            </div>
            <ActionMessage {...state} />
          </div>
          <div className="dialog__actions dialog__actions--footer">
            <button className="secondary-button" type="button" onClick={() => dialogRef.current?.close()}>Cancel</button>
            <SubmitButton className="primary-button" pendingLabel="Creating…">Create user</SubmitButton>
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
        className="table-button inline-flex items-center gap-1 hover:bg-blue-100 transition-colors"
        type="button"
        onClick={() => editRef.current?.showModal()}
      >
        <Pencil className="h-3 w-3" />
        <span>Edit</span>
      </button>
      <button
        className="table-button inline-flex items-center gap-1 hover:bg-blue-100 transition-colors"
        type="button"
        onClick={() => passwordRef.current?.showModal()}
      >
        <KeyRound className="h-3 w-3" />
        <span>Password</span>
      </button>
      <form
        action={statusAction}
        onSubmit={(event) => {
          if (!window.confirm(`${user.is_active ? "Deactivate" : "Activate"} ${user.username}?`)) {
            event.preventDefault();
          }
        }}
      >
        <input type="hidden" name="user_id" value={user.id} />
        <input type="hidden" name="is_active" value={String(!user.is_active)} />
        <button
          className="table-button inline-flex items-center gap-1 hover:bg-slate-200 transition-colors"
          type="submit"
          disabled={isSelf}
        >
          {user.is_active ? (
            <>
              <UserX className="h-3 w-3 text-red-500" />
              <span>Deactivate</span>
            </>
          ) : (
            <>
              <UserCheck className="h-3 w-3 text-emerald-600" />
              <span>Activate</span>
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
            eyebrow="Account administration"
            title="Edit user"
            description="Update this member's workspace profile and access level."
            icon={UserCog}
            titleId={`edit-${user.id}`}
            onClose={() => editRef.current?.close()}
          />
          <div className="admin-form__body">
            <div className="dialog-user-identity flex items-center gap-3 p-3 rounded-xl border border-slate-100 bg-slate-50/70">
              <Avatar className="h-10 w-10">
                <AvatarFallback>{initials(user.display_name)}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <strong className="block text-sm font-semibold text-slate-800">{user.display_name}</strong>
                <small className="text-slate-500">@{user.username}</small>
              </div>
              <Badge variant={user.is_active ? "success" : "warning"}>
                {user.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            <div className="form-grid">
              <label className="form-field">
                <span className="field-label">Display name <b>Required</b></span>
                <input className="field-control" name="display_name" required maxLength={100} defaultValue={user.display_name} placeholder="e.g. CyVerse" />
                <small className="field-hint">The name shown across the workspace.</small>
              </label>
              <label className="form-field">
                <span className="field-label">Team</span>
                <input className="field-control" name="team" maxLength={100} defaultValue={user.team ?? ""} placeholder="e.g. Data Platform" />
                <small className="field-hint">Optional organizational group.</small>
              </label>
            </div>
            <label className="form-field">
              <span className="field-label">Role <b>Required</b></span>
              <select className="field-control" name="role" defaultValue={user.role} disabled={isSelf}>
                <option value="member">Member</option>
                <option value="admin">Administrator</option>
              </select>
              {isSelf && <input type="hidden" name="role" value={user.role} />}
              <small className="field-hint">{isSelf ? "Use another administrator account to change your role." : "Administrators can manage all accounts."}</small>
            </label>
            <ActionMessage {...editState} />
          </div>
          <div className="dialog__actions dialog__actions--footer">
            <button className="secondary-button" type="button" onClick={() => editRef.current?.close()}>Cancel</button>
            <SubmitButton className="primary-button" pendingLabel="Saving…">Save changes</SubmitButton>
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
            eyebrow="Account security"
            title="Reset password"
            description="Set a new temporary password and revoke this user's existing sessions."
            icon={KeyRound}
            titleId={`password-${user.id}`}
            onClose={() => passwordRef.current?.close()}
          />
          <div className="admin-form__body">
            <div className="dialog-user-identity flex items-center gap-3 p-3 rounded-xl border border-slate-100 bg-slate-50/70">
              <Avatar className="h-10 w-10">
                <AvatarFallback>{initials(user.display_name)}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <strong className="block text-sm font-semibold text-slate-800">{user.display_name}</strong>
                <small className="text-slate-500">@{user.username}</small>
              </div>
            </div>
            <label className="form-field">
              <span className="field-label">New temporary password <b>Required</b></span>
              <input className="field-control" name="password" type="password" required minLength={8} maxLength={128} autoComplete="new-password" placeholder="At least 8 characters" />
              <small className="field-hint">Use 8–128 characters. All existing tokens for this user will be invalidated.</small>
            </label>
            <ActionMessage {...passwordState} />
          </div>
          <div className="dialog__actions dialog__actions--footer">
            <button className="secondary-button" type="button" onClick={() => passwordRef.current?.close()}>Cancel</button>
            <SubmitButton className="primary-button" pendingLabel="Updating…">Update password</SubmitButton>
          </div>
        </form>
      </dialog>
    </div>
  );
}

export function UserManagement({ data, currentUserId, query }: { data: UserListResponse; currentUserId: string; query: string }) {
  const router = useRouter();
  const [isSearchPending, startSearchTransition] = useTransition();
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  const pageHref = (page: number) => `/admin/users?page=${page}${query ? `&query=${encodeURIComponent(query)}` : ""}`;

  function submitSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const nextQuery = String(formData.get("query") ?? "").trim().slice(0, 100);
    const nextPath = nextQuery ? `/admin/users?query=${encodeURIComponent(nextQuery)}` : "/admin/users";
    startSearchTransition(() => router.push(nextPath));
  }

  return (
    <main className="admin-page">
      <header className="admin-header">
        <div>
          <p className="eyebrow eyebrow--blue">Administration</p>
          <h1>User Management</h1>
          <p>Create accounts and control access to the internal workspace.</p>
        </div>
        <CreateUserDialog />
      </header>
      <section className="admin-card">
        <form className="user-search" onSubmit={submitSearch}>
          <label className="flex items-center gap-2">
            <span className="sr-only">Search users</span>
            <Search className="h-4 w-4 text-slate-400 shrink-0" aria-hidden="true" />
            <input name="query" defaultValue={query} maxLength={100} placeholder="Search by name, username, or team…" />
          </label>
          <button className="secondary-button" type="submit" disabled={isSearchPending}>
            {isSearchPending ? "Searching…" : "Search"}
          </button>
        </form>
        {data.items.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Team</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th><span className="sr-only">Actions</span></th>
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
                    <td>
                      <Badge variant={user.role === "admin" ? "default" : "secondary"}>
                        {user.role}
                      </Badge>
                    </td>
                    <td>
                      <Badge variant={user.is_active ? "success" : "warning"}>
                        {user.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td>{userDateFormatter.format(new Date(user.created_at))}</td>
                    <td><UserActions user={user} currentUserId={currentUserId} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No users found</strong>
            <p>Try another search or create a new account.</p>
          </div>
        )}
        <footer className="pagination">
          <span>{data.total} user{data.total === 1 ? "" : "s"}</span>
          <div>
            <Link aria-disabled={data.page <= 1} className={data.page <= 1 ? "disabled" : ""} href={pageHref(Math.max(1, data.page - 1))}>Previous</Link>
            <span>Page {data.page} of {totalPages}</span>
            <Link aria-disabled={data.page >= totalPages} className={data.page >= totalPages ? "disabled" : ""} href={pageHref(Math.min(totalPages, data.page + 1))}>Next</Link>
          </div>
        </footer>
      </section>
    </main>
  );
}

