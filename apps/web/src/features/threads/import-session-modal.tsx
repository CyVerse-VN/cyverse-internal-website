"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, KeyRound, Layers, Loader2, UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ThreadsAccountItem } from "./types";

interface ImportSessionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultAccountId?: string;
  onSuccess?: () => void;
}

export function ImportSessionModal({
  open,
  onOpenChange,
  defaultAccountId,
  onSuccess,
}: ImportSessionModalProps) {
  const [accounts, setAccounts] = useState<ThreadsAccountItem[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<string>(defaultAccountId ?? "");
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [jsonText, setJsonText] = useState("");
  const [detectedBundleAccounts, setDetectedBundleAccounts] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleClose = () => {
    setFile(null);
    setJsonText("");
    setDetectedBundleAccounts([]);
    setError(null);
    onOpenChange(false);
  };

  useEffect(() => {
    if (!open) return;
    let ignore = false;
    fetch("/api/threads/accounts")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch accounts list");
        return res.json();
      })
      .then((data) => {
        if (!ignore) {
          const list: ThreadsAccountItem[] = data.accounts ?? [];
          setAccounts(list);
          if (defaultAccountId) {
            setSelectedAccount(defaultAccountId);
          } else {
            const firstMissing = list.find((a) => a.enabled && (!a.has_session || a.is_expired)) ?? list[0];
            if (firstMissing) {
              setSelectedAccount(firstMissing.id);
            }
          }
          setLoadingAccounts(false);
        }
      })
      .catch(() => {
        if (!ignore) {
          setError("Failed to load configured Threads accounts.");
          setLoadingAccounts(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [open, defaultAccountId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setError(null);
      const reader = new FileReader();
      reader.onload = (event) => {
        const text = String(event.target?.result ?? "");
        setJsonText(text);

        // Detect whether this is a bundled threads_sessions.json or a single account session
        try {
          const parsed = JSON.parse(text);
          if (typeof parsed === "object" && parsed !== null) {
            if ("sessions" in parsed && typeof parsed.sessions === "object" && parsed.sessions !== null) {
              setDetectedBundleAccounts(Object.keys(parsed.sessions));
            } else if (!("cookies" in parsed)) {
              const keys = Object.keys(parsed).filter((k) => typeof parsed[k] === "object" && parsed[k] !== null && "cookies" in parsed[k]);
              if (keys.length > 0) {
                setDetectedBundleAccounts(keys);
              } else {
                setDetectedBundleAccounts([]);
              }
            } else {
              setDetectedBundleAccounts([]);
            }
          }
        } catch {
          setDetectedBundleAccounts([]);
        }
      };
      reader.readAsText(selected);
    }
  };

  const handleUpload = async () => {
    if (!jsonText.trim()) {
      setError("Please select a session JSON file (e.g. threads_sessions.json or acc_01.json).");
      return;
    }

    let parsedData: unknown;
    try {
      parsedData = JSON.parse(jsonText);
    } catch {
      setError("The provided file is not valid JSON.");
      return;
    }

    if (typeof parsedData !== "object" || parsedData === null) {
      setError("Invalid session format: JSON must be an object.");
      return;
    }

    setUploading(true);
    setError(null);

    try {
      if (detectedBundleAccounts.length > 0) {
        // Upload bundled sessions
        const res = await fetch("/api/threads/sessions/batch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ bundle: parsedData }),
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail ?? "Failed to import session bundle.");
        }
        toast.success(`Imported and activated ${data.total_imported} account session(s) from bundle successfully!`);
      } else {
        // Upload single account session
        if (!selectedAccount) {
          throw new Error("Please select a target account for this session file.");
        }
        if (!("cookies" in parsedData)) {
          throw new Error("Single session file must contain a 'cookies' array.");
        }
        const res = await fetch(`/api/threads/accounts/${encodeURIComponent(selectedAccount)}/session`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_data: parsedData }),
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail ?? "Failed to import session.");
        }
        toast.success(`Session for account '${selectedAccount}' imported and saved to database successfully!`);
      }

      handleClose();
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error importing session.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : handleClose())}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-indigo-500" />
            <DialogTitle>Import Threads Session</DialogTitle>
          </div>
          <DialogDescription>
            Upload a unified <code>threads_sessions.json</code> containing all accounts or an individual <code>acc_01.json</code>.
            Sessions are saved to PostgreSQL and instantly synchronized with cloud containers.
          </DialogDescription>
        </DialogHeader>

        {loadingAccounts ? (
          <div className="flex items-center justify-center py-8 text-sm text-slate-500">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading accounts...
          </div>
        ) : (
          <div className="space-y-4 py-2">
            {/* Account Selector (only when NOT uploading a bundle) */}
            {detectedBundleAccounts.length > 0 ? (
              <div className="rounded-lg bg-indigo-50/80 p-3 text-xs text-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-300 space-y-1 border border-indigo-200 dark:border-indigo-800">
                <div className="flex items-center gap-1.5 font-semibold">
                  <Layers className="h-4 w-4" />
                  Unified Bundle Detected (threads_sessions.json)
                </div>
                <p>
                  Found <strong>{detectedBundleAccounts.length}</strong> accounts in bundle:{" "}
                  <code>{detectedBundleAccounts.join(", ")}</code>. All will be imported simultaneously!
                </p>
              </div>
            ) : (
              <div className="space-y-1.5">
                <label htmlFor="account-select" className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Target Account
                </label>
                {accounts.length > 0 ? (
                  <select
                    id="account-select"
                    value={selectedAccount}
                    onChange={(e) => setSelectedAccount(e.target.value)}
                    className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none dark:border-slate-800 dark:bg-slate-900"
                  >
                    {accounts.map((acc) => {
                      const statusText = !acc.has_session
                        ? "⚠ Missing Session"
                        : acc.is_expired
                        ? "❌ Session Expired"
                        : "✓ Active Session";
                      return (
                        <option key={acc.id} value={acc.id}>
                          {acc.id} {acc.username ? `(@${acc.username})` : ""} [{statusText}]
                        </option>
                      );
                    })}
                  </select>
                ) : (
                  <div className="text-sm text-amber-600 dark:text-amber-400">
                    No Threads accounts configured. Make sure THREADS_ACCOUNTS is configured in your environment.
                  </div>
                )}
              </div>
            )}

            {/* File Upload Area */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Session File (threads_sessions.json or {selectedAccount ? `${selectedAccount}.json` : "acc_01.json"})
              </label>
              <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-6 text-center transition-colors hover:border-indigo-400 hover:bg-indigo-50/20 dark:border-slate-700 dark:bg-slate-900/50">
                <UploadCloud className="mb-2 h-8 w-8 text-slate-400" />
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  {file ? file.name : "Click to select threads_sessions.json or acc_01.json"}
                </span>
                <span className="text-xs text-slate-400">
                  Supports unified bundle (threads_sessions.json) or individual Playwright session files
                </span>
                <input
                  type="file"
                  accept=".json,application/json"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
            </div>

            {/* Error Message */}
            {error && (
              <div className="rounded-md bg-red-50 p-3 text-xs text-red-600 dark:bg-red-950/50 dark:text-red-400">
                {error}
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" type="button" onClick={() => onOpenChange(false)} disabled={uploading}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleUpload}
            disabled={uploading || loadingAccounts || (!detectedBundleAccounts.length && !selectedAccount) || !jsonText}
            className="gap-1.5"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving to Database...
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4" />
                {detectedBundleAccounts.length > 0 ? "Save All to Database" : "Save & Activate Session"}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
