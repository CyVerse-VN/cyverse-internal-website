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

  return (
    <main className="dashboard-page">
      <header className="topbar">
        <label className="dashboard-search">
          <span className="sr-only">Search tools</span>
          <Search className="h-4 w-4 text-slate-400 shrink-0" aria-hidden="true" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search tools, models, datasets…"
          />
        </label>
        <button
          className="icon-button topbar-notifications transition-colors hover:bg-slate-100 text-slate-600"
          type="button"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>
        <ThemeToggle />
        {accountMenu}
      </header>


      <div className="dashboard-body">
        {notice === "admin-required" && (
          <p className="notice-banner" role="status">
            Administrator access is required for User Management.
          </p>
        )}
        <section className="welcome-row">
          <div>
            <span className="demo-pill">Demo data</span>
            <h1>
              Hello, {firstName} <span aria-hidden="true">👋</span>
            </h1>
            <p>Welcome to CyVerse Internal Tools</p>
            <small>Build, experiment, and deploy explainable deepfake detection — together.</small>
          </div>
          <blockquote>
            “More trustworthy media for a safer tomorrow.”<cite>— CyVerse</cite>
          </blockquote>
        </section>

        <section className="metric-grid" aria-label="Workspace overview">
          <article className="metric-card metric-card--blue hover:shadow-md transition-shadow">
            <span>
              <Wrench className="h-5 w-5" />
            </span>
            <strong>
              6<small>Available Tools</small>
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
              12<small>Datasets</small>
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
              8<small>Experiments</small>
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
              5<small>Team Members</small>
            </strong>
            <b>
              <ArrowRight className="h-4 w-4" />
            </b>
          </article>
        </section>

        <section className="dashboard-section">
          <div className="section-heading">
            <h2>Popular Tools</h2>
            <span>Curated for your team</span>
          </div>
          {tools.length ? (
            <div className="tool-grid">
              {tools.map((tool) => {
                const Icon = TOOL_ICONS[tool.name] ?? Wrench;
                return (
                  <article className="tool-card hover:shadow-lg transition-all" key={tool.name}>
                    <span className={`tool-icon tool-icon--${tool.tone}`}>
                      <Icon className="h-5 w-5" />
                    </span>
                    <h3>{tool.name}</h3>
                    <p>{tool.description}</p>
                    <button type="button" disabled>
                      Coming soon
                    </button>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              <strong>No tools found</strong>
              <p>Try a different search term.</p>
            </div>
          )}
        </section>

        <section className="dashboard-section">
          <div className="section-heading">
            <h2>Recent Activity</h2>
            <span>Sample activity</span>
          </div>
          <div className="activity-list hover:shadow-sm transition-shadow">
            <div className="activity-icon bg-blue-100 text-blue-700">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <strong>Deepfake Detection analysis completed</strong>
              <p>Sample video · 2 hours ago</p>
            </div>
            <Badge variant="success" className="ml-auto">
              Completed
            </Badge>
          </div>
        </section>
      </div>
    </main>
  );
}

