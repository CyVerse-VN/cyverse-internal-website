import { redirect } from "next/navigation";

import { BrandMark } from "@/components/brand-mark";
import { LoginForm } from "@/features/auth/login-form";
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
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-visual">
          <BrandMark inverse href="/" />
          <div className="login-copy">
            <p className="eyebrow">CyVerse internal platform</p>
            <h2>Toward a more trusted digital world</h2>
            <p>Explainable AI for a safer, more authentic online environment.</p>
          </div>
          <div className="digital-globe" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </div>
        </div>
        <div className="login-panel">
          <div className="login-panel__content">
            <p className="eyebrow eyebrow--blue">Secure workspace</p>
            <h1 id="login-title">Welcome back</h1>
            <p className="login-intro">Sign in to access CyVerse internal tools.</p>
            <LoginForm nextPath={nextPath} />
            <p className="login-help">Need an account? Contact your administrator.</p>
          </div>
        </div>
      </section>
    </main>
  );
}
