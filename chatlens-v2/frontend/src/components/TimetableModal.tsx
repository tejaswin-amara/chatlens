"use client";

import React, { useState, useEffect } from "react";
import { X, Calendar, RefreshCw, CheckCircle2, AlertTriangle, XCircle, MapPin } from "lucide-react";
import type { TodayTimetable } from "@/types";
import { useApi } from "@/hooks/useApi";

interface TimetableModalProps {
  open: boolean;
  onClose: () => void;
  onToast: (message: string, type: "success" | "error" | "info") => void;
}

export default function TimetableModal({ open, onClose, onToast }: TimetableModalProps) {
  const api = useApi();
  const [data, setData] = useState<TodayTimetable | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [period, setPeriod] = useState<number>(1);
  const [courseCode, setCourseCode] = useState("25SC2107E");
  const [room, setRoom] = useState("");
  const [status, setStatus] = useState<"OVERRIDE" | "CANCELLED">("OVERRIDE");

  const loadTimetable = async () => {
    setLoading(true);
    try {
      const res = await api.loadTodayTimetable();
      setData(res);
    } catch {
      onToast("Failed to load today's timetable", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      loadTimetable();
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (status === "OVERRIDE" && !room.trim()) {
      onToast("Please specify the new room number", "error");
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.submitTimetableOverride({
        period,
        course_code: courseCode,
        room: status === "OVERRIDE" ? room.trim() : undefined,
        status,
        summary: `Updated via ChatLens Web: P${period} ${courseCode} -> ${status === "OVERRIDE" ? room : "CANCELLED"}`,
      });
      if (res.success) {
        onToast(`Timetable updated! P${period} marked as ${res.status}.`, "success");
        setRoom("");
        loadTimetable();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to record timetable update";
      onToast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-brand-card border border-brand-border rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 px-6 border-b border-brand-border flex items-center justify-between bg-brand-bg/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <Calendar size={18} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-brand-text">Today&apos;s Timetable &amp; Room Changes</h2>
              <p className="text-xs text-brand-text-dim">
                {data?.day ? `${data.day}, ${data.date}` : "Loading schedule..."} • Real-time overrides
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadTimetable}
              disabled={loading}
              aria-label="Refresh timetable"
              className="p-1.5 rounded-lg border border-brand-border text-brand-text-dim hover:text-brand-text transition-colors"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            </button>
            <button
              onClick={onClose}
              aria-label="Close timetable modal"
              className="p-1.5 rounded-lg border border-brand-border text-brand-text-dim hover:text-brand-text transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Slots List */}
          <div>
            <h3 className="text-xs font-semibold text-brand-text-dim uppercase tracking-wider mb-3">
              Scheduled Periods
            </h3>
            {loading && !data ? (
              <div className="py-8 text-center text-xs text-brand-text-dim">Loading schedule...</div>
            ) : !data?.slots || data.slots.length === 0 ? (
              <div className="p-4 rounded-lg bg-brand-bg/40 border border-brand-border/60 text-center text-xs text-brand-text-dim">
                🎉 No classes scheduled for today!
              </div>
            ) : (
              <div className="grid gap-2 sm:grid-cols-2">
                {data.slots.map((slot) => {
                  const isCancelled = slot.status === "CANCELLED";
                  const isOverride = slot.status === "OVERRIDE";
                  return (
                    <div
                      key={slot.period}
                      className={`p-3.5 rounded-lg border transition-all ${
                        isCancelled
                          ? "bg-red-500/5 border-red-500/30 opacity-75"
                          : isOverride
                          ? "bg-amber-500/10 border-amber-500/40"
                          : "bg-brand-bg/50 border-brand-border/70"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <span className="text-[0.7rem] font-bold px-1.5 py-0.5 rounded bg-brand-border text-brand-text">
                          P{slot.period}
                        </span>
                        {isCancelled ? (
                          <span className="inline-flex items-center gap-1 text-[0.68rem] font-medium text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded">
                            <XCircle size={11} /> Cancelled
                          </span>
                        ) : isOverride ? (
                          <span className="inline-flex items-center gap-1 text-[0.68rem] font-medium text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                            <AlertTriangle size={11} /> Override
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[0.68rem] font-medium text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                            <CheckCircle2 size={11} /> Normal
                          </span>
                        )}
                      </div>
                      <div className="text-sm font-semibold text-brand-text truncate">
                        {slot.course}
                      </div>
                      <div className="text-xs text-brand-text-dim flex items-center gap-1 mt-1">
                        <MapPin size={12} className="shrink-0 text-brand-accent" />
                        <span className={isCancelled ? "line-through" : "font-mono font-medium text-brand-text"}>
                          {slot.room}
                        </span>
                        {slot.faculty && <span className="truncate">• {slot.faculty}</span>}
                      </div>
                      {slot.override && (
                        <div className="text-[0.68rem] text-amber-300/90 mt-1 italic">
                          {slot.override}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Update Timetable Form */}
          <div className="pt-4 border-t border-brand-border">
            <h3 className="text-xs font-semibold text-brand-text-dim uppercase tracking-wider mb-3">
              Submit Room Override or Cancellation
            </h3>
            <form onSubmit={handleSubmit} className="space-y-3 bg-brand-bg/40 p-4 rounded-xl border border-brand-border/60">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[0.72rem] text-brand-text-dim mb-1">Period</label>
                  <select
                    value={period}
                    onChange={(e) => setPeriod(Number(e.target.value))}
                    className="w-full bg-brand-card border border-brand-border rounded-lg px-2.5 py-1.5 text-xs text-brand-text outline-none focus:border-brand-accent"
                  >
                    {[1, 2, 3, 4, 5, 7, 8, 9].map((p) => (
                      <option key={p} value={p}>
                        Period {p}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[0.72rem] text-brand-text-dim mb-1">Course Code</label>
                  <input
                    type="text"
                    value={courseCode}
                    onChange={(e) => setCourseCode(e.target.value.toUpperCase())}
                    placeholder="e.g. 25SC2107E or ML"
                    required
                    className="w-full bg-brand-card border border-brand-border rounded-lg px-2.5 py-1.5 text-xs text-brand-text outline-none focus:border-brand-accent uppercase"
                  />
                </div>
                <div>
                  <label className="block text-[0.72rem] text-brand-text-dim mb-1">Action</label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value as "OVERRIDE" | "CANCELLED")}
                    className="w-full bg-brand-card border border-brand-border rounded-lg px-2.5 py-1.5 text-xs text-brand-text outline-none focus:border-brand-accent"
                  >
                    <option value="OVERRIDE">Room Override</option>
                    <option value="CANCELLED">Cancel Class</option>
                  </select>
                </div>
              </div>

              {status === "OVERRIDE" && (
                <div>
                  <label className="block text-[0.72rem] text-brand-text-dim mb-1">New Room Number</label>
                  <input
                    type="text"
                    value={room}
                    onChange={(e) => setRoom(e.target.value.toUpperCase())}
                    placeholder="e.g. HC-15C, H-301A, H-006"
                    required
                    className="w-full bg-brand-card border border-brand-border rounded-lg px-2.5 py-1.5 text-xs text-brand-text outline-none focus:border-brand-accent uppercase"
                  />
                </div>
              )}

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-brand-accent hover:bg-brand-accent/90 text-white text-xs font-medium transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {submitting ? "Applying..." : "Update Timetable"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
