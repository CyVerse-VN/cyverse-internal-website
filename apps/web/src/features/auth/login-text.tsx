"use client";

import { useLanguage } from "@/lib/i18n/context";

export function LoginTitle() {
  const { t } = useLanguage();
  return (
    <div className="login-title-group">
      <h1 id="login-title">{t("auth.welcomeBack")}</h1>
      <p className="login-intro">{t("auth.subtitle")}</p>
    </div>
  );
}

export function LoginFooter() {
  const { t } = useLanguage();
  return <p className="login-footer">{t("auth.needAccount")}</p>;
}
