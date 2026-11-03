"use client";

import { AlertTriangle } from "lucide-react";
import styles from "./threads.module.css";

export function CrossSessionDedup({ enabled, onChange }: {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
}) {
  return (
    <label className={styles.dedupChoice} data-enabled={enabled}>
      <input type="checkbox" checked={enabled} onChange={(event) => onChange(event.target.checked)} />
      <span>
        <strong><AlertTriangle size={15} aria-hidden="true" /> Exclude posts from previous sessions</strong>
        <small>
          {enabled
            ? "On: posts already saved in your previous sessions will be excluded, so this collection may contain fewer posts."
            : "Off: posts from previous sessions can be collected again. Duplicate results within this collection are still merged."}
        </small>
      </span>
    </label>
  );
}
