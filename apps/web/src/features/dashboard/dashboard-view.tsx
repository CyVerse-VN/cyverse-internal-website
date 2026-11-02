"use client";

import { useMemo, useState } from "react";
import {
  ArrowRight,
  Bell,
  CheckCircle2,
  Database,
  Eye,
  FlaskConical,
  Search,
  ShieldAlert,
  Users,
  Video,
  Wrench,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "@/components/language-toggle";
import { useLanguage } from "@/lib/i18n/context";
import type { AuthUser } from "@/lib/auth/types";


export const popularTools = [
  {
    name: "Deepfake Detection",
    description: "Detect manipulated images and videos with explainable AI.",
    icon: "◩",
    tone: "coral",
  },
  {
    name: "Video Analysis",
    description: "Analyze video and extract key frames and metadata.",
    icon: "▧",
    tone: "violet",
  },
  {
    name: "Explainability Viewer",
    description: "Visualize model explanations and attention maps.",
    icon: "▥",
    tone: "green",
  },
  {
    name: "Dataset Manager",
    description: "Manage, preview, and label training datasets.",
    icon: "◉",
    tone: "blue",
  },
];

const TOOL_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  "Deepfake Detection": ShieldAlert,
  "Video Analysis": Video,
  "Explainability Viewer": Eye,
  "Dataset Manager": Database,
};

export function filterTools(query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return popularTools;
  }
  return popularTools.filter(
    (tool) =>
      tool.name.toLowerCase().includes(normalized) ||
      tool.description.toLowerCase().includes(normalized),
  );
}

export function DashboardView({
  user,
  notice,
  accountMenu,
}: {
  user: AuthUser;
  notice?: string;
  accountMenu?: React.ReactNode;
}) {
  const [query, setQuery] = useState("");
  const tools = useMemo(() => filterTools(query), [query]);
  const firstName = user.display_name.split(/\s+/)[0] || user.username;
  const { t } = useLanguage();

  return (
    <main className="dashboard-page">
      <header className="topbar">
        <label className="dashboard-search">
          <span className="sr-only">Search tools</span>
          <Search className="h-4 w-4 text-slate-400 shrink-0" aria-hidden="true" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("topbar.searchPlaceholder")}
          />
        </label>
        <button
          className="icon-button topbar-notifications transition-colors hover:bg-slate-100 text-slate-600"
          type="button"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>
        <LanguageToggle />
        <ThemeToggle />
        {accountMenu}
      </header>


      <div className="dashboard-body">
        {notice === "admin-required" && (
          <p className="notice-banner" role="status">
            {t("dashboard.adminRequiredNotice")}
          </p>
        )}
        <section className="welcome-row">
          <div>
            <span className="demo-pill">{t("dashboard.demoPill")}</span>
            <h1>
              {t("dashboard.greeting")}, {firstName} <span aria-hidden="true">👋</span>
            </h1>
            <p>{t("dashboard.subtitle")}</p>
            <small>{t("dashboard.tagline")}</small>
          </div>
          <blockquote>
            {t("dashboard.quote")}<cite>{t("dashboard.quoteAuthor")}</cite>
          </blockquote>
        </section>

        <section className="metric-grid" aria-label="Workspace overview">
          <article className="metric-card metric-card--blue hover:shadow-md transition-shadow">
            <span>
              <Wrench className="h-5 w-5" />
            </span>
            <strong>
              6<small>{t("dashboard.availableToolsMetric")}</small>
            </strong>
            <b>
              <ArrowRight className="h-4 w-4" />
            </b>
          </article>
          <article className="metric-card metric-card--green hover:shadow-md transition-shadow">
            <span>
              <Database className="h-5 w-5" />
            </span>
            <strong>
              12<small>{t("dashboard.datasetsMetric")}</small>
            </strong>
            <b>
              <ArrowRight className="h-4 w-4" />
            </b>
          </article>
          <article className="metric-card metric-card--violet hover:shadow-md transition-shadow">
            <span>
              <FlaskConical className="h-5 w-5" />
            </span>
            <strong>
              8<small>{t("dashboard.experimentsMetric")}</small>
            </strong>
            <b>
              <ArrowRight className="h-4 w-4" />
            </b>
          </article>
          <article className="metric-card metric-card--orange hover:shadow-md transition-shadow">
            <span>
              <Users className="h-5 w-5" />
            </span>
            <strong>
              5<small>{t("dashboard.teamMembersMetric")}</small>
            </strong>
            <b>
              <ArrowRight className="h-4 w-4" />
            </b>
          </article>
        </section>

        <section className="dashboard-section">
          <div className="section-heading">
            <h2>{t("dashboard.popularTools")}</h2>
            <span>{t("dashboard.popularToolsSubtitle")}</span>
          </div>
          {tools.length ? (
            <div className="tool-grid">
              {tools.map((tool) => {
                const Icon = TOOL_ICONS[tool.name] ?? Wrench;
                const toolTitle =
                  tool.name === "Deepfake Detection"
                    ? t("dashboard.deepfakeTitle")
                    : tool.name === "Video Analysis"
                      ? t("dashboard.videoTitle")
                      : tool.name === "Explainability Viewer"
                        ? t("dashboard.explainTitle")
                        : tool.name === "Dataset Manager"
                          ? t("dashboard.datasetTitle")
                          : tool.name;
                const toolDesc =
                  tool.name === "Deepfake Detection"
                    ? t("dashboard.deepfakeDesc")
                    : tool.name === "Video Analysis"
                      ? t("dashboard.videoDesc")
                      : tool.name === "Explainability Viewer"
                        ? t("dashboard.explainDesc")
                        : tool.name === "Dataset Manager"
                          ? t("dashboard.datasetDesc")
                          : tool.description;
                return (
                  <article className="tool-card hover:shadow-lg transition-all" key={tool.name}>
                    <span className={`tool-icon tool-icon--${tool.tone}`}>
                      <Icon className="h-5 w-5" />
                    </span>
                    <h3>{toolTitle}</h3>
                    <p>{toolDesc}</p>
                    <button type="button" disabled>
                      {t("dashboard.comingSoon")}
                    </button>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              <strong>{t("dashboard.noToolsFound")}</strong>
              <p>{t("dashboard.noToolsDesc")}</p>
            </div>
          )}
        </section>

        <section className="dashboard-section">
          <div className="section-heading">
            <h2>{t("dashboard.recentActivity")}</h2>
            <span>{t("dashboard.sampleActivity")}</span>
          </div>
          <div className="activity-list hover:shadow-sm transition-shadow">
            <div className="activity-icon bg-blue-100 text-blue-700">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <strong>{t("dashboard.activityItemTitle")}</strong>
              <p>{t("dashboard.activityItemMeta")}</p>
            </div>
            <Badge variant="success" className="ml-auto">
              {t("dashboard.completed")}
            </Badge>
          </div>
        </section>
      </div>
    </main>
  );
}

