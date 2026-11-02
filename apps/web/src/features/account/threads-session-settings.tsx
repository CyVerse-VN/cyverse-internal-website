"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Download, KeyRound, Loader2, RefreshCw, Upload, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ImportSessionModal } from "@/features/threads/import-session-modal";
import type { ThreadsAccountItem } from "@/features/threads/types";

export function ThreadsSessionSettings() {
  const [accounts, setAccounts] = useState<ThreadsAccountItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [targetAccount, setTargetAccount] = useState<string | undefined>(undefined);

  const fetchAccounts = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const res = await fetch("/api/threads/accounts", { cache: "no-store" });
      if (!res.ok) {
        throw new Error("Failed to load accounts");
      }
      const data = await res.json();
      setAccounts(data.accounts ?? []);
    } catch {
      setError("Unable to load Threads accounts from backend.");
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    fetch("/api/threads/accounts", { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load accounts");
        return res.json();
      })
      .then((data) => {
        if (!ignore) {
          setAccounts(data.accounts ?? []);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!ignore) {
          setError("Unable to load Threads accounts from backend.");
          setLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, []);

  const handleOpenModal = (accountId?: string) => {
    setTargetAccount(accountId);
    setModalOpen(true);
  };

  const activeCount = accounts.filter((a) => a.has_session && !a.is_expired).length;
  const expiredCount = accounts.filter((a) => a.has_session && a.is_expired).length;
  const missingCount = accounts.filter((a) => !a.has_session).length;

  return (
    <section className="settings-card">
      <div className="settings-card__heading flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            className="settings-card__icon flex items-center justify-center rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400"
            aria-hidden="true"
          >
            <KeyRound className="h-5 w-5" />
          </span>
          <div>
            <h2>Threads Sessions (Admin)</h2>
            <p>Quản lý phiên đăng nhập Threads dùng chung cho cả nhóm.</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => handleOpenModal(undefined)}
            className="gap-1.5 text-xs font-medium"
          >
            <Upload className="h-3.5 w-3.5 text-indigo-500" />
            Import JSON (Bundle)
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            asChild
            className="gap-1.5 text-xs text-slate-600 dark:text-slate-300"
          >
            <a href="/api/threads/sessions/export" download="threads_sessions.json">
              <Download className="h-3.5 w-3.5" />
              Export JSON
            </a>
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => fetchAccounts()}
            disabled={loading || refreshing}
            className="gap-1.5 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      <div className="space-y-4 pt-3">
        {error && (
          <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-600 dark:bg-red-950/50 dark:text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Status Overview */}
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span>Đã cấu hình: <strong>{accounts.length}</strong></span>
          <span>•</span>
          <span className="text-emerald-600 dark:text-emerald-400">Hoạt động: <strong>{activeCount}</strong></span>
          {expiredCount > 0 && (
            <>
              <span>•</span>
              <span className="text-red-600 dark:text-red-400 font-medium">Hết hạn: <strong>{expiredCount}</strong></span>
            </>
          )}
          {missingCount > 0 && (
            <>
              <span>•</span>
              <span className="text-amber-600 dark:text-amber-400">Chưa có session: <strong>{missingCount}</strong></span>
            </>
          )}
        </div>

        {/* Account List */}
        {loading ? (
          <div className="flex items-center justify-center py-8 text-sm text-slate-500">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Đang kiểm tra trạng thái phiên...
          </div>
        ) : accounts.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-xs text-slate-500 dark:border-slate-800">
            Chưa có tài khoản Threads nào được cấu hình. Vui lòng thêm <code>THREADS_ACCOUNTS</code> vào biến môi trường.
          </div>
        ) : (
          <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900/50">
            {accounts.map((account) => {
              const isExpired = account.has_session && account.is_expired;
              const isActive = account.has_session && !account.is_expired;

              return (
                <div
                  key={account.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 transition-colors hover:bg-slate-50/50 dark:hover:bg-slate-800/40"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-slate-800 dark:text-slate-200">
                        {account.id}
                      </span>
                      {account.username && (
                        <span className="text-xs text-slate-400">
                          (@{account.username})
                        </span>
                      )}
                      {isActive && (
                        <Badge variant="success" className="gap-1 text-[11px] py-0">
                          <CheckCircle2 className="h-3 w-3" />
                          Active
                        </Badge>
                      )}
                      {isExpired && (
                        <Badge variant="destructive" className="gap-1 text-[11px] py-0">
                          <AlertTriangle className="h-3 w-3" />
                          Hết hạn
                        </Badge>
                      )}
                      {!account.has_session && (
                        <Badge variant="secondary" className="gap-1 text-[11px] py-0 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800">
                          <XCircle className="h-3 w-3" />
                          Chưa có session
                        </Badge>
                      )}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {isActive && account.expires_at ? (
                        <span>Hết hạn vào: {new Date(account.expires_at).toLocaleDateString()}</span>
                      ) : isActive ? (
                        <span>Phiên đăng nhập hợp lệ</span>
                      ) : isExpired && account.expires_at ? (
                        <span className="text-red-500 font-medium">
                          Đã hết hạn vào {new Date(account.expires_at).toLocaleDateString()} — cần cập nhật file JSON mới
                        </span>
                      ) : (
                        <span>Chưa có file session — import JSON để kích hoạt</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenModal(account.id)}
                      className="gap-1.5 text-xs"
                    >
                      <Upload className="h-3.5 w-3.5" />
                      {account.has_session ? "Cập nhật riêng" : "Import JSON"}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Information Notice */}
        <div className="rounded-lg bg-slate-50 p-4 text-xs text-slate-600 dark:bg-slate-900/60 dark:text-slate-300 space-y-1.5 border border-slate-200 dark:border-slate-800">
          <p className="font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-1.5">
            <KeyRound className="h-3.5 w-3.5 text-indigo-500" />
            Quy tắc gom chung 1 file JSON (threads_sessions.json) &amp; Đồng bộ
          </p>
          <ul className="list-disc pl-4 space-y-1 text-slate-500 dark:text-slate-400">
            <li>
              <strong>Gom chung 1 file (Unified Bundle):</strong> Bạn có thể xuất (Export) hoặc nhập (Import) cả 3 tài khoản cùng lúc qua 1 tệp duy nhất tên là <code>threads_sessions.json</code>.
            </li>
            <li>
              <strong>Chạy ở Local:</strong> Backend local tự động ưu tiên đọc file <code>threads_sessions.json</code> hoặc các file <code>acc_01.json</code> trong <code>apps/backend/.local/threads/sessions/</code>.
            </li>
            <li>
              <strong>Chạy trên Web (Render):</strong> Khi Admin import tệp JSON, toàn bộ session được lưu bền vững vào database PostgreSQL (<code>threads_account_sessions</code>) và tự động đồng bộ vào container cào dữ liệu khi container khởi động lại.
            </li>
            <li>
              <strong>Dùng chung cho cả nhóm:</strong> Mọi thành viên đều dùng chung các session đang hoạt động mà Admin đã kích hoạt.
            </li>
          </ul>
        </div>
      </div>

      <ImportSessionModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        defaultAccountId={targetAccount}
        onSuccess={() => fetchAccounts()}
      />
    </section>
  );
}
