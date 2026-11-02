"use client";

import { Clock3, LoaderCircle, MessagesSquare, PanelLeftClose, PanelLeftOpen, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useLanguage } from "@/lib/i18n/context";
import type { ThreadsRun } from "./types";
import styles from "./threads.module.css";

export function ThreadsHistory({
  items,
  selectedId,
  collapsed,
  loading,
  loadingMore,
  hasMore,
  title,
  emptyHint,
  onToggle,
  onSelect,
  onNew,
  onLoadMore,
}: {
  items: ThreadsRun[];
  selectedId: string | null;
  collapsed: boolean;
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  title?: string;
  emptyHint?: string;
  onToggle: () => void;
  onSelect: (id: string) => void;
  onNew: () => void;
  onLoadMore: () => void;
}) {
  const { t, language } = useLanguage();

  return (
    <aside
      className={`${styles.history} ${styles.historyRail}`}
      data-collapsed={collapsed}
      aria-label="Session history"
    >
      <div className={styles.railHeading}>
        <h2 className={styles.railTitle} data-collapsed={collapsed}>
          <Clock3 size={15} />
          <span>{title ?? t("threads.historyHeading")}</span>
        </h2>
        <button
          type="button"
          className={styles.panelToggle}
          aria-label={collapsed ? "Expand history" : "Collapse history"}
          title={
            collapsed
              ? language === "vi"
                ? "Mở rộng lịch sử phiên"
                : "Expand history"
              : language === "vi"
                ? "Thu gọn lịch sử phiên"
                : "Collapse history"
          }
          aria-expanded={!collapsed}
          aria-controls="threads-history-content"
          onClick={onToggle}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      <Button
        variant="outline"
        size="sm"
        onClick={onNew}
        aria-label={t("threads.newCollection")}
        title={t("threads.newCollection")}
        className={styles.railNew}
      >
        <Plus size={16} />
        <span className={styles.railNewText}>{t("threads.newCollection")}</span>
      </Button>

      <div
        id="threads-history-content"
        className={styles.railContent}
        data-collapsed={collapsed}
      >
        {loading ? (
          <p role="status" className={styles.hint}>
            {t("threads.loadingHistory")}
          </p>
        ) : items.length === 0 ? (
          <p className={styles.hint}>{emptyHint ?? t("threads.emptyHistoryHint")}</p>
        ) : (
          <ul className={styles.historyList}>
            {items.map((item) => {
              const isSelected = selectedId === item.id;
              const queryText = item.request.query || "Untitled session";
              const dateText = new Date(item.created_at).toLocaleDateString(
                language === "vi" ? "vi-VN" : "en",
                { month: "short", day: "numeric" },
              );
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className={styles.historyItemBtn}
                    onClick={() => onSelect(item.id)}
                    aria-current={isSelected ? "page" : undefined}
                    title={`${queryText} (${item.post_count} posts · ${dateText})`}
                  >
                    <span className={styles.historyItemIcon} aria-hidden="true">
                      <MessagesSquare size={14} />
                    </span>
                    <span className={styles.historyEntry}>
                      <strong>{queryText}</strong>
                      <small>
                        {dateText} · {item.visibility} · {item.post_count} posts
                      </small>
                    </span>
                    <Badge
                      variant={
                        item.status === "completed"
                          ? "success"
                          : item.status === "failed"
                            ? "destructive"
                            : item.status === "running"
                              ? "default"
                              : item.status === "queued"
                                ? "warning"
                                : "secondary"
                      }
                      className={styles.historyItemBadge}
                    >
                      {item.deletion_requested
                        ? language === "vi"
                          ? "Đang xóa"
                          : "Deleting"
                        : item.status === "queued"
                          ? language === "vi"
                            ? "Chờ chạy"
                            : "Queued"
                          : item.status === "running"
                            ? language === "vi"
                              ? "Đang chạy"
                              : "Running"
                            : item.status === "completed"
                              ? language === "vi"
                                ? "Xong"
                                : "Done"
                              : item.status === "failed"
                                ? language === "vi"
                                  ? "Lỗi"
                                  : "Failed"
                                : item.status}
                    </Badge>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {hasMore && !collapsed && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onLoadMore}
            disabled={loadingMore}
            className={styles.railLoadMore}
          >
            {loadingMore ? (
              <LoaderCircle size={14} className={styles.spinner} />
            ) : null}
            {t("threads.loadMoreCollections")}
          </Button>
        )}
      </div>
    </aside>
  );
}

