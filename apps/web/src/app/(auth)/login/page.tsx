import { redirect } from "next/navigation";

import { BrandMark } from "@/components/brand-mark";
import { LanguageToggle } from "@/components/language-toggle";
import { ThemeToggle } from "@/components/theme-toggle";
import { LoginForm } from "@/features/auth/login-form";
import { LoginTitle, LoginFooter } from "@/features/auth/login-text";
import { getSafeNextPath } from "@/lib/auth/safe-redirect";
import { getCurrentUser } from "@/lib/auth/server";

export const dynamic = "force-dynamic";

interface LoginPageProps {
  searchParams: Promise<{ next?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  if (await getCurrentUser()) {
    redirect("/dashboard");
  }
  const { next } = await searchParams;
  const nextPath = getSafeNextPath(next);

  return (
    <main className="login-page">
      <div className="login-quick-actions">
        <LanguageToggle />
        <ThemeToggle />
      </div>
      <div className="login-container">
        <section className="login-card" aria-labelledby="login-title">
          <div className="login-header">
            <BrandMark />
            <LoginTitle />
          </div>
          <LoginForm nextPath={nextPath} />
        </section>
        <LoginFooter />
      </div>
    </main>
  );
}
