"use client";

import Link, { useLinkStatus } from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  Database,
  FileText,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  Menu,
  MessagesSquare,
  Sparkles,
  Users,
} from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { AccountMenu } from "@/components/account-menu";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "@/components/language-toggle";
import { useLanguage } from "@/lib/i18n/context";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { logoutAction } from "@/features/auth/actions";
import type { AuthUser } from "@/lib/auth/types";


const memberNav = [
  { href: "/dashboard", label: "Home", key: "nav.home", icon: LayoutDashboard },
  { href: "/tools/research", label: "AI Research Tool", key: "nav.research", icon: Sparkles },
  { href: "/tools/threads", label: "Threads Scraper", key: "nav.threads", icon: MessagesSquare },
  { href: "", label: "Datasets", key: "nav.datasets", icon: Database },
  { href: "", label: "Experiments", key: "nav.experiments", icon: FlaskConical },
  { href: "", label: "Monitoring", key: "nav.monitoring", icon: Activity },
  { href: "", label: "Documents", key: "nav.documents", icon: FileText },
];

function NavigationPendingIndicator() {
  const { pending } = useLinkStatus();
  return (
    <span
      className={`nav-link__pending ${pending ? "nav-link__pending--visible" : ""}`}
      aria-hidden="true"
    />
  );
}

export function DashboardShell({ user, children }: { user: AuthUser; children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { t } = useLanguage();

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      setSidebarCollapsed(window.localStorage.getItem("cyverse.sidebar.collapsed") === "true");
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  function toggleSidebar(): void {
    setSidebarCollapsed((current) => {
      const next = !current;
      window.localStorage.setItem("cyverse.sidebar.collapsed", String(next));
      return next;
    });
  }
  const initials = user.display_name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className={`app-shell ${sidebarCollapsed ? "app-shell--sidebar-collapsed" : ""}`}>
      <button
        className="mobile-menu-button"
        type="button"
        onClick={() => setMenuOpen((open) => !open)}
        aria-controls="primary-navigation"
        aria-expanded={menuOpen}
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
        <span className="sr-only">Toggle navigation</span>
      </button>
      {menuOpen && (
        <button
          className="sidebar-scrim"
          type="button"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside
        className={`sidebar ${menuOpen ? "sidebar--open" : ""} ${sidebarCollapsed ? "sidebar--collapsed" : ""}`}
        id="primary-navigation"
      >
        <div className="sidebar__brand">
          <BrandMark compact inverse href="/dashboard" onClick={() => setMenuOpen(false)} />
          <button
            className="sidebar-collapse-button"
            type="button"
            onClick={toggleSidebar}
            aria-label={sidebarCollapsed ? t("nav.expand") : t("nav.collapse")}
            title={sidebarCollapsed ? t("nav.expand") : t("nav.collapse")}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
        </div>
        <nav aria-label="Primary navigation">
          {memberNav.map((item) => {
            const Icon = item.icon;
            const label = t(item.key);
            return item.href ? (
              <Link
                key={item.label}
                className={`nav-link ${pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`)) ? "nav-link--active" : ""}`}
                href={item.href}
                onClick={() => setMenuOpen(false)}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span className="nav-link__label">{label}</span>
                <NavigationPendingIndicator />
              </Link>
            ) : (
              <span className="nav-link nav-link--disabled" key={item.label} title="Coming soon">
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span className="nav-link__label">{label}</span>
                <small>{t("nav.soon")}</small>
              </span>
            );
          })}
          {user.role === "admin" && (
            <Link
              className={`nav-link ${pathname.startsWith("/admin") ? "nav-link--active" : ""}`}
              href="/admin/users"
              onClick={() => setMenuOpen(false)}
            >
              <Users className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="nav-link__label">{t("nav.users")}</span>
              <NavigationPendingIndicator />
            </Link>
          )}
        </nav>
        <div className="sidebar__footer">
          <div className="sidebar-user">
            <Avatar className="h-8 w-8 ring-1 ring-white/20">
              <AvatarFallback className="bg-blue-600/80 text-xs font-bold text-white">
                {initials}
              </AvatarFallback>
            </Avatar>
            <span>
              <strong>{user.display_name}</strong>
              <small>{user.team ?? "CyVerse"}</small>
            </span>
          </div>
          <form action={logoutAction}>
            <button className="nav-link logout-button" type="submit">
              <LogOut className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="nav-link__label">{t("account.signOut")}</span>
            </button>
          </form>
        </div>
      </aside>

      <div className="app-content">
        {pathname !== "/dashboard" && (
          <header className="topbar shell-topbar">
            <div className="shell-topbar__context">
              <small>CyVerse internal workspace</small>
              <strong>
                {pathname.startsWith("/settings")
                  ? t("topbar.account")
                  : pathname.startsWith("/tools/research")
                    ? t("nav.research")
                    : pathname.startsWith("/tools/threads")
                      ? t("nav.threads")
                    : t("topbar.admin")}
              </strong>
            </div>
            <div className="flex items-center gap-2 ml-auto">
              <LanguageToggle />
              <ThemeToggle />
              <AccountMenu user={user} />
            </div>
          </header>
        )}
        {children}

      </div>
    </div>
  );
}
