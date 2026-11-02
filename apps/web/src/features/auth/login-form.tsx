"use client";

import { useActionState, useState } from "react";

import { SubmitButton } from "@/components/submit-button";
import { loginAction } from "@/features/auth/actions";
import { useLanguage } from "@/lib/i18n/context";
import { INITIAL_ACTION_STATE } from "@/lib/auth/types";

export function LoginForm({ nextPath }: { nextPath: string }) {
  const [state, formAction] = useActionState(loginAction, INITIAL_ACTION_STATE);
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState("");
  const { t } = useLanguage();

  return (
    <form
      className="login-form"
      action={formAction}
      onReset={(event) => {
        event.preventDefault();
        const password = event.currentTarget.elements.namedItem("password");
        if (password instanceof HTMLInputElement) password.value = "";
      }}
    >
      <input type="hidden" name="next" value={nextPath} />
      <div className="login-field-group">
        <label htmlFor="username">{t("auth.username")}</label>
        <div className="field-shell">
          <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          <input
            id="username"
            name="username"
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            minLength={3}
            maxLength={64}
            pattern="[A-Za-z0-9._-]+"
            placeholder={t("auth.usernamePlaceholder")}
            aria-describedby="login-username-rule"
            required
          />
        </div>
        <small className="login-field-hint" id="login-username-rule">
          {t("auth.usernameHint")}
        </small>
      </div>

      <div className="login-field-group">
        <label htmlFor="password">{t("auth.password")}</label>
        <div className="field-shell">
          <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            minLength={8}
            maxLength={128}
            placeholder={t("auth.passwordPlaceholder")}
            required
          />
          <button
            className="password-toggle"
            type="button"
            onClick={() => setShowPassword((current) => !current)}
            aria-label={showPassword ? t("auth.hide") : t("auth.show")}
            aria-pressed={showPassword}
          >
            {showPassword ? t("auth.hide") : t("auth.show")}
          </button>
        </div>
      </div>

      {state.status === "error" && (
        <p className="form-message form-message--error" role="alert">
          {state.message}
        </p>
      )}

      <SubmitButton className="primary-button login-button" pendingLabel={t("auth.signingIn")}>
        {t("auth.signIn")}
      </SubmitButton>
    </form>
  );
}
