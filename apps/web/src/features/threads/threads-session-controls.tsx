"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { threadsApi } from "./api";
import { threadsRunSchema, type ThreadsRun } from "./types";
import styles from "./threads.module.css";

export function ThreadsSessionControls({ run, onUpdated }: {
  run: ThreadsRun;
  onUpdated: (run: ThreadsRun) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function changeVisibility(visibility: "public" | "private") {
    setBusy(true); setError(null);
    try {
      onUpdated(await threadsApi(`/runs/${run.id}`, threadsRunSchema, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ visibility }),
      }));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not update visibility.");
    } finally { setBusy(false); }
  }

  async function deleteSession() {
    if (!window.confirm("Permanently delete this session, all saved posts and comments, and its Cloudinary text archive? An active collection will be stopped.")) return;
    setBusy(true); setError(null);
    try {
      onUpdated(await threadsApi(`/runs/${run.id}`, threadsRunSchema, { method: "DELETE" }));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not delete session.");
    } finally { setBusy(false); }
  }

  return <div className={styles.sessionControls}>
    <div className={styles.sessionActions}>
      {run.can_manage ? <>
        <label className={styles.field}>
          <span>Visibility</span>
          <select aria-label="Saved session visibility" value={run.visibility} disabled={busy || run.deletion_requested}
            onChange={(event) => void changeVisibility(event.target.value === "private" ? "private" : "public")}>
            <option value="public">Public</option><option value="private">Private</option>
          </select>
        </label>
        <Button variant="outline" size="sm" disabled={busy || run.deletion_requested} onClick={() => void deleteSession()}>
          <Trash2 size={14} />{run.deletion_requested ? "Deleting session…" : "Delete session"}
        </Button>
      </> : <span>{run.visibility === "public" ? "Public session" : "Private session"}</span>}
      <span className={styles.hint}>{run.post_count} saved posts · {run.comment_count} saved comments</span>
    </div>
    {run.deletion_requested ? <p className={styles.notice} role="status">
      Deleting Cloudinary and database data. This continues after you close the page.
      {run.storage_error && " Cleanup is waiting for cloud storage and will retry automatically."}
    </p> : <p className={styles.hint} role="status">
      Collection data is saved in the database.
    </p>}
    <details className={styles.sessionMetadata}>
      <summary>Session metadata</summary>
      <dl>
        <dt>Session ID</dt><dd>{run.id}</dd>
        <dt>Created by</dt><dd>{run.owner?.display_name ?? run.owner?.id ?? "Unavailable"}</dd>
        <dt>Created</dt><dd>{new Date(run.created_at).toLocaleString()}</dd>
        <dt>Started</dt><dd>{run.started_at ? new Date(run.started_at).toLocaleString() : "Not started"}</dd>
        <dt>Finished</dt><dd>{run.completed_at ? new Date(run.completed_at).toLocaleString() : "In progress"}</dd>
      </dl>
    </details>
    {error && <p className={styles.error} role="alert">{error}</p>}
  </div>;
}
