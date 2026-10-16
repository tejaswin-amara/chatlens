"use client";

import { useEffect, useState } from "react";
import { X, Bot, RefreshCw, CheckCircle2, Clock, History, AlertCircle } from "lucide-react";
import clsx from "clsx";
import type { SparkStatus } from "@/types";

interface SparkStatusModalProps {
  open: boolean;
  onClose: () => void;
  onRefresh: () => Promise<SparkStatus>;
}

export default function SparkStatusModal({ open, onClose, onRefresh }: SparkStatusModalProps) {
  const [status, setStatus] = useState<SparkStatus | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    let cancelled = false;
    onRefresh()
      .then((res) => {
        if (!cancelled) setStatus(res);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, onRefresh]);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl bg-brand-bg border border-brand-border rounded-brand shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-4 px-6 border-b border-brand-border flex items-center justify-between bg-brand-card/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-brand-accent/10 border border-brand-accent/20 flex items-center justify-center text-brand-accent">
              <Bot size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-brand-text-bright">
                SPARK Personal Assistant Daemon
              </h2>
              <p className="text-[0.7rem] text-brand-text-dim">
                Headless Telegram & Google Workspace Bridge (IST)
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setLoading(true);
                onRefresh()
                  .then(setStatus)
                  .finally(() => setLoading(false));
              }}
              disabled={loading}
              className="p-1.5 rounded-brand-sm border border-brand-border hover:bg-white/5 text-brand-text-dim hover:text-brand-text transition-colors disabled:opacity-50"
              title="Refresh status"
              aria-label="Refresh status"
            >
              <RefreshCw size={14} className={clsx(loading && "animate-spin-custom")} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-brand-sm border border-brand-border hover:bg-white/5 text-brand-text-dim hover:text-brand-text transition-colors"
              aria-label="Close dialog"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-[0.8rem]">
          {loading && !status ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <div className="w-6 h-6 border-2 border-brand-accent border-t-transparent rounded-full animate-spin-custom" />
              <span className="text-brand-text-dim text-xs">Querying SPARK SQLite State...</span>
            </div>
          ) : !status ? (
            <div className="text-center py-10 text-brand-text-dim">
              Could not retrieve daemon status.
            </div>
          ) : (
            <>
              {/* Status Overview Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="bg-brand-card border border-brand-border rounded-brand-sm p-3.5">
                  <div className="text-[0.7rem] text-brand-text-dim mb-1">Daemon Status</div>
                  <div className="flex items-center gap-1.5 font-semibold">
                    <span
                      className={clsx(
                        "w-2 h-2 rounded-full",
                        status.status === "online" ? "bg-emerald-400" : "bg-amber-400"
                      )}
                    />
                    <span
                      className={
                        status.status === "online" ? "text-emerald-400" : "text-amber-400"
                      }
                    >
                      {status.status.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="bg-brand-card border border-brand-border rounded-brand-sm p-3.5">
                  <div className="text-[0.7rem] text-brand-text-dim mb-1">Execution Mode</div>
                  <div className="font-semibold text-brand-accent uppercase tracking-wide">
                    {status.mode}
                  </div>
                </div>

                <div className="bg-brand-card border border-brand-border rounded-brand-sm p-3.5">
                  <div className="text-[0.7rem] text-brand-text-dim mb-1">Ingested Messages</div>
                  <div className="font-semibold text-brand-text-bright">
                    {status.seen_messages.toLocaleString()}
                  </div>
                </div>
              </div>

              {status.message && (
                <div className="p-3 bg-brand-card/40 border border-brand-border rounded-brand-sm text-brand-text-dim flex items-center gap-2">
                  <AlertCircle size={16} className="text-brand-accent shrink-0" />
                  <span>{status.message}</span>
                </div>
              )}

              {/* Pending Approvals */}
              <div>
                <div className="flex items-center gap-2 mb-2 font-medium text-brand-text-bright">
                  <Clock size={14} className="text-amber-400" />
                  <span>Pending Confirmations (Bot Owner Review)</span>
                  <span className="text-xs px-1.5 py-0.2 rounded bg-amber-400/10 text-amber-400 border border-amber-400/20">
                    {status.pending.length}
                  </span>
                </div>

                {status.pending.length === 0 ? (
                  <div className="p-3.5 border border-brand-border/60 rounded-brand-sm bg-brand-card/20 text-brand-text-dim text-xs">
                    No pending actions waiting for owner approval.
                  </div>
                ) : (
                  <div className="border border-brand-border rounded-brand-sm overflow-hidden divide-y divide-brand-border">
                    {status.pending.map((p) => (
                      <div key={p.id} className="p-2.5 px-3 bg-brand-card/30 flex items-center justify-between text-xs">
                        <span className="font-mono text-brand-accent">#{p.id}</span>
                        <span className="text-brand-text truncate max-w-[280px]">{p.event}</span>
                        <span className="px-2 py-0.5 rounded text-[0.65rem] bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium">
                          {p.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Recent Writes & Undo Log */}
              <div>
                <div className="flex items-center gap-2 mb-2 font-medium text-brand-text-bright">
                  <History size={14} className="text-brand-accent" />
                  <span>Recent State Writes & Undo Ledger</span>
                </div>

                {status.writes.length === 0 ? (
                  <div className="p-3.5 border border-brand-border/60 rounded-brand-sm bg-brand-card/20 text-brand-text-dim text-xs">
                    No writes recorded in the current session.
                  </div>
                ) : (
                  <div className="border border-brand-border rounded-brand-sm overflow-hidden divide-y divide-brand-border">
                    {status.writes.map((w) => (
                      <div key={w.id} className="p-2.5 px-3 bg-brand-card/30 flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-brand-text-dim">#{w.id}</span>
                          <span className="font-semibold text-brand-text-bright">{w.kind}</span>
                          <span className="text-brand-text-dim font-mono text-[0.7rem] truncate max-w-[200px]">
                            {w.event_id}
                          </span>
                        </div>
                        {w.undone ? (
                          <span className="text-rose-400 text-[0.7rem] bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                            Undone
                          </span>
                        ) : (
                          <span className="text-emerald-400 text-[0.7rem] bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                            <CheckCircle2 size={12} /> Applied
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
