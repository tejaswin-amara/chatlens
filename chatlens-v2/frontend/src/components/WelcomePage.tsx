"use client";

import { Send, Calendar, Clock, Bot, BookOpen, Sparkles } from "lucide-react";
import { FormatAi } from "@/components/FormatAi";

interface WelcomePageProps {
  globalSummary: string | null;
  onOpenTimetable?: () => void;
  onOpenDeadlines?: () => void;
  onOpenStatus?: () => void;
  onOpenExamPrep?: () => void;
}

export function WelcomePage({
  globalSummary,
  onOpenTimetable,
  onOpenDeadlines,
  onOpenStatus,
  onOpenExamPrep,
}: WelcomePageProps) {
  const telegramBotUrl = "https://t.me/Tejaswin_Amara_PA_bot?start=web";

  return (
    <div className="flex-1 flex items-center justify-center p-6 motion-safe:animate-fade-in">
      <div className="max-w-4xl w-full text-center">
        {/* App Hero / Brand */}
        <div className="text-[3.2rem] mb-3">🚀</div>
        <h1 className="text-3xl md:text-4xl font-bold gradient-text mb-2 tracking-tight">
          Welcome to ChatLens
        </h1>
        <p className="text-brand-text-dim text-sm max-w-xl mx-auto mb-8 leading-relaxed">
          SPARK PA Academic Assistant for KL University. Launch the bot directly in Telegram
          via <code className="text-brand-accent bg-brand-accent/10 px-1.5 py-0.5 rounded text-xs font-mono">/start</code> or explore academic modules below.
        </p>

        {/* Primary Start in Telegram Button */}
        <div className="mb-10 max-w-md mx-auto">
          <a
            href={telegramBotUrl}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Start in Telegram (/start)"
            className="w-full group px-6 py-4 rounded-brand border border-brand-accent/40 bg-gradient-to-r from-brand-accent/20 to-sky-500/20 hover:from-brand-accent/30 hover:to-sky-500/30 text-brand-text-bright font-semibold text-base flex items-center justify-center gap-3 transition-all shadow-lg shadow-brand-accent/10 hover:shadow-brand-accent/20 spring-click"
          >
            <div className="p-2 rounded-full bg-brand-accent/20 group-hover:bg-brand-accent/30 text-brand-accent transition-colors">
              <Send size={20} className="translate-x-0.5" />
            </div>
            <div className="text-left">
              <div className="font-bold flex items-center gap-2">
                Start in Telegram <span className="text-xs bg-brand-accent/20 text-brand-accent px-2 py-0.5 rounded-full font-mono">/start</span>
              </div>
              <div className="text-[0.75rem] font-normal text-brand-text-dim">
                Instant schedules, live attendance &amp; deadline alerts
              </div>
            </div>
          </a>
        </div>

        {/* Quick-Access Academic Modals */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-10 text-left">
          {onOpenTimetable && (
            <button
              onClick={onOpenTimetable}
              className="p-3.5 rounded-brand border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-brand-text-bright transition-colors flex flex-col gap-1.5 spring-click"
              aria-label="Open weekly timetable"
            >
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs">
                <Calendar size={16} /> Timetable
              </div>
              <p className="text-[0.72rem] text-brand-text-dim leading-snug">
                Weekly periods, labs &amp; room overrides
              </p>
            </button>
          )}

          {onOpenDeadlines && (
            <button
              onClick={onOpenDeadlines}
              className="p-3.5 rounded-brand border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 text-brand-text-bright transition-colors flex flex-col gap-1.5 spring-click"
              aria-label="Open deadlines and milestones"
            >
              <div className="flex items-center gap-2 text-indigo-400 font-semibold text-xs">
                <Clock size={16} /> Deadlines
              </div>
              <p className="text-[0.72rem] text-brand-text-dim leading-snug">
                ALM, projects, fee dates &amp; voice briefs
              </p>
            </button>
          )}

          {onOpenStatus && (
            <button
              onClick={onOpenStatus}
              className="p-3.5 rounded-brand border border-brand-accent/30 bg-brand-accent/10 hover:bg-brand-accent/20 text-brand-text-bright transition-colors flex flex-col gap-1.5 spring-click"
              aria-label="Open system status"
            >
              <div className="flex items-center gap-2 text-brand-accent font-semibold text-xs">
                <Bot size={16} /> Daemon Status
              </div>
              <p className="text-[0.72rem] text-brand-text-dim leading-snug">
                Live polling, heartbeat &amp; SQLite state
              </p>
            </button>
          )}

          {onOpenExamPrep && (
            <button
              onClick={onOpenExamPrep}
              className="p-3.5 rounded-brand border border-purple-500/30 bg-purple-500/10 hover:bg-purple-500/20 text-brand-text-bright transition-colors flex flex-col gap-1.5 spring-click"
              aria-label="Open exam preparation"
            >
              <div className="flex items-center gap-2 text-purple-300 font-semibold text-xs">
                <BookOpen size={16} /> Exam Prep
              </div>
              <p className="text-[0.72rem] text-brand-text-dim leading-snug">
                CO sequence flow, marks &amp; guidelines
              </p>
            </button>
          )}
        </div>

        {/* Global Summary */}
        <div className="text-left">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-brand-accent" />
            <h2 className="text-sm font-semibold text-brand-text-bright">
              Global Chat Summary
            </h2>
          </div>

          <div className="glass-panel rounded-brand p-6 relative overflow-hidden">
            <div
              className="absolute inset-0 rounded-brand bg-brand-accent/10 pointer-events-none"
              style={{ animation: "ambientGlow 8s ease-in-out 2 alternate" }}
            />

            <div className="relative z-10 text-[0.85rem] text-brand-text leading-relaxed">
              {globalSummary === null ? (
                <div className="flex flex-col items-center gap-3 py-4">
                  <div className="w-5 h-5 border-2 border-brand-accent border-t-transparent rounded-full motion-safe:animate-spin" />
                  <div className="w-full space-y-2">
                    <div className="h-2.5 w-full bg-brand-border/50 rounded motion-safe:animate-pulse" />
                    <div className="h-2.5 w-4/5 bg-brand-border/50 rounded motion-safe:animate-pulse" />
                    <div className="h-2.5 w-3/5 bg-brand-border/50 rounded motion-safe:animate-pulse" />
                  </div>
                </div>
              ) : (
                <FormatAi text={globalSummary} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
