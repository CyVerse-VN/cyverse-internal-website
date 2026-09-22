"use client";

import { useActionState, useState } from "react";

import { SubmitButton } from "@/components/submit-button";
import { loginAction } from "@/features/auth/actions";
import { INITIAL_ACTION_STATE } from "@/lib/auth/types";

export function LoginForm({ nextPath }: { nextPath: string }) {
  const [state, formAction] = useActionState(loginAction, INITIAL_ACTION_STATE);
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState("");

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
      <label htmlFor="username">Username</label>
      <div className="field-shell">
        <span aria-hidden="true">◎</span>
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
          placeholder="e.g. cyverse"
          aria-describedby="login-username-rule"
          required
        />
      </div>
      <small className="login-field-hint" id="login-username-rule">No spaces. Use letters, numbers, dots, underscores, or hyphens.</small>

      <label htmlFor="password">Password</label>
      <div className="field-shell">
        <span aria-hidden="true">◇</span>
        <input
          id="password"
          name="password"
          type={showPassword ? "text" : "password"}
          autoComplete="current-password"
          minLength={8}
          maxLength={128}
          placeholder="Enter your password"
          required
        />
        <button
          className="password-toggle"
          type="button"
          onClick={() => setShowPassword((current) => !current)}
          aria-label={showPassword ? "Hide password" : "Show password"}
          aria-pressed={showPassword}
        >
          {showPassword ? "Hide" : "Show"}
        </button>
      </div>

      {state.status === "error" && (
        <p className="form-message form-message--error" role="alert">
          {state.message}
        </p>
      )}

      <SubmitButton className="primary-button login-button" pendingLabel="Signing in…">
        Sign in <span aria-hidden="true">→</span>
      </SubmitButton>
    </form>
  );
}
