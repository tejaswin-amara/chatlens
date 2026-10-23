"use client";

import React, { useState, useEffect } from "react";
import { X, Clock, Mic, Volume2, Sparkles, RefreshCw, Calendar, CheckSquare } from "lucide-react";
import type { DeadlinesData } from "@/types";
import { useApi } from "@/hooks/useApi";

interface DeadlinesModalProps {
  open: boolean;
  onClose: () => void;
  onToast: (message: string, type: "success" | "error" | "info") => void;
}

export default function DeadlinesModal({ open, onClose, onToast }: DeadlinesModalProps) {
  const api = useApi();
  const [data, setData] = useState<DeadlinesData | null>(null);
  const [loading, setLoading] = useState(false);
  const [briefingLoading, setBriefingLoading] = useState(false);
  const [briefingScript, setBriefingScript] = useState<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [customQuery, setCustomQuery] = useState("");

  const loadDeadlines = async () => {
    setLoading(true);
    try {
      const res = await api.loadDeadlines();
      setData(res);
    } catch {
      onToast("Failed to load upcoming deadlines", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      loadDeadlines();
    } else {
      // Stop speech when closing
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        setIsSpeaking(false);
      }
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSpeak = (text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      onToast("Speech synthesis is not supported in this browser.", "info");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const handleSayDeadlines = async (queryText?: string) => {
    setBriefingLoading(true);
    try {
      const script = await api.sayDeadlines(queryText || customQuery || undefined);
      setBriefingScript(script);
      handleSpeak(script);
      onToast("AI Briefing generated!", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to generate briefing";
      onToast(msg, "error");
    } finally {
      setBriefingLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-brand-card border border-brand-border rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 px-6 border-b border-brand-border flex items-center justify-between bg-brand-bg/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
              <Clock size={18} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-brand-text">Academic Deadlines & Milestones</h2>
              <p className="text-xs text-brand-text-dim">
                Google Gemini AI Schedule & Assignment Briefing
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadDeadlines}
              disabled={loading}
              aria-label="Refresh deadlines"
              className="p-1.5 rounded-lg border border-brand-border text-brand-text-dim hover:text-brand-text transition-colors"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            </button>
            <button
              onClick={onClose}
              aria-label="Close deadlines modal"
              className="p-1.5 rounded-lg border border-brand-border text-brand-text-dim hover:text-brand-text transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* AI Voice Briefing Action Banner */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-pink-500/10 border border-indigo-500/20">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-brand-text flex items-center gap-1.5">
                  <Sparkles size={16} className="text-indigo-400" />
                  Say the Deadlines (AI Voice Briefing)
                </h3>
                <p className="text-xs text-brand-text-dim mt-0.5">
                  Listen to an energetic, spoken briefing of today&apos;s schedule and upcoming tests.
                </p>
              </div>
              <button
                onClick={() => handleSayDeadlines()}
                disabled={briefingLoading}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-500/20 disabled:opacity-50 shrink-0"
              >
                {briefingLoading ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" /> Synthesizing...
                  </>
                ) : isSpeaking ? (
                  <>
                    <Volume2 size={14} className="animate-pulse" /> Speaking...
                  </>
                ) : (
                  <>
                    <Mic size={14} /> Say Deadlines
                  </>
                )}
              </button>
            </div>

            {/* Custom query input */}
            <div className="mt-3 flex items-center gap-2">
              <input
                type="text"
                value={customQuery}
                onChange={(e) => setCustomQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSayDeadlines()}
                placeholder="Ask specific briefing (e.g. 'What is due for ML and exams?')..."
                className="flex-1 bg-brand-bg/80 border border-brand-border rounded-lg px-3 py-1.5 text-xs text-brand-text placeholder-brand-text-dim outline-none focus:border-indigo-400"
              />
              <button
                onClick={() => handleSayDeadlines()}
                disabled={briefingLoading || !customQuery.trim()}
                className="px-3 py-1.5 rounded-lg bg-brand-card hover:bg-brand-border border border-brand-border text-xs text-brand-text font-medium disabled:opacity-40 transition-colors"
              >
                Ask
              </button>
            </div>

            {/* Briefing Output Card */}
            {briefingScript && (
              <div className="mt-4 p-3.5 bg-brand-card/90 rounded-lg border border-brand-border/80 animate-fade-in">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[0.68rem] font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-1">
                    <Volume2 size={12} /> Gemini Audio Script
                  </span>
                  <button
                    onClick={() => handleSpeak(briefingScript)}
                    className="text-[0.7rem] text-brand-text-dim hover:text-brand-text underline"
                  >
                    Replay Voice
                  </button>
                </div>
                <p className="text-xs text-brand-text leading-relaxed font-sans italic">
                  &ldquo;{briefingScript}&rdquo;
                </p>
              </div>
            )}
          </div>

          {/* Academic Calendar Milestones */}
          <div>
            <h3 className="text-xs font-semibold text-brand-text-dim uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Calendar size={13} /> Academic Calendar Milestones
            </h3>
            {loading && !data ? (
              <div className="py-4 text-center text-xs text-brand-text-dim">Loading milestones...</div>
            ) : !data?.milestones || data.milestones.length === 0 ? (
              <div className="p-3 text-center text-xs text-brand-text-dim bg-brand-bg/40 rounded-lg border border-brand-border/60">
                No upcoming calendar milestones found.
              </div>
            ) : (
              <div className="space-y-2">
                {data.milestones.map((m, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-brand-bg/50 border border-brand-border/70 flex items-center justify-between"
                  >
                    <div>
                      <div className="text-xs font-semibold text-brand-text">{m.title}</div>
                      <div className="text-[0.7rem] text-brand-text-dim">
                        {m.term ? `${m.term} • ` : ""}Date: {m.date}
                      </div>
                    </div>
                    <span
                      className={`text-[0.68rem] font-semibold px-2 py-0.5 rounded-full ${
                        m.days_remaining <= 3
                          ? "bg-red-500/10 text-red-400 border border-red-500/20"
                          : m.days_remaining <= 10
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          : "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                      }`}
                    >
                      {m.days_remaining === 0 ? "Today!" : `in ${m.days_remaining} days`}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Pending Tasks & Assignments */}
          <div>
            <h3 className="text-xs font-semibold text-brand-text-dim uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <CheckSquare size={13} /> Pending Course Assignments
            </h3>
            {!data?.tasks || data.tasks.length === 0 ? (
              <div className="p-3 text-center text-xs text-brand-text-dim bg-brand-bg/40 rounded-lg border border-brand-border/60">
                🎉 All tasks and assignments are completed!
              </div>
            ) : (
              <div className="space-y-2">
                {data.tasks.map((task) => (
                  <div
                    key={task.id}
                    className="p-3 rounded-lg bg-brand-bg/50 border border-brand-border/70 flex items-center justify-between"
                  >
                    <div className="text-xs font-medium text-brand-text">{task.summary}</div>
                    <span className="text-[0.68rem] font-semibold px-2 py-0.5 rounded bg-brand-border text-brand-text-dim">
                      {task.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
