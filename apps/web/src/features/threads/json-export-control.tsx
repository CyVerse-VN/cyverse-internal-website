"use client";

import { useId, useState } from "react";
import { ArrowDownToLine } from "lucide-react";
import styles from "./threads.module.css";

export function JsonExportControl({ runId }: { runId: string }) {
  const [detail, setDetail] = useState("basic");
  const labelId = useId();
  return <div>
    <label htmlFor={labelId}>JSON detail: </label>
    <select id={labelId} value={detail} onChange={(event) => setDetail(event.target.value)}>
      <option value="basic">Basic — posts and comments</option>
      <option value="standard">Standard — metadata and statistics</option>
      <option value="full">Full — includes source data</option>
    </select>{" "}
    <a href={`/api/threads/runs/${encodeURIComponent(runId)}/export?format=json&detail=${detail}`}
      download className={styles.exportActionBtn}>
      <ArrowDownToLine size={14} /> Download JSON
    </a>
  </div>;
}
