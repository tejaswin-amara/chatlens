"use client";

import { Activity, Sparkles, Flag, List, Zap } from "lucide-react";
import clsx from "clsx";

interface ChatHeaderProps {
  chatName: string;
  view: "messages" | "dashboard";
  onViewChange: (view: "messages" | "dashboard") => void;
  onInsight: (type: string) => void;
  onAnalyze: () => void;
  aiLoading: boolean;
}

const insightButtons = [
  { type: "relationship_dynamics", label: "Dynamics", icon: Activity },
  { type: "vibe_check", label: "Vibe", icon: Sparkles },
  { type: "flags", label: "Flags", icon: Flag },
  { type: "recap", label: "Recap", icon: List },
] as const;

export default function ChatHeader({
  chatName,
  view,
  onViewChange,
  onInsight,
  onAnalyze,
  aiLoading,
}: ChatHeaderProps) {
  return (
    <div className="p-4 px-6 border-b border-brand-border flex items-center gap-3 bg-gradient-to-b from-brand-accent/5 to-transparent flex-wrap">
      <div className="text-[1.05rem] font-semibold text-brand-text-bright flex-1 pl-10 md:pl-0">
        {chatName}
      </div>

      {/* Tab switcher */}
      <div className="flex gap-2 bg-white/5 p-1 rounded-brand-sm">
        {(["messages", "dashboard"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => onViewChange(tab)}
            className={clsx(
              "px-3 py-1.5 rounded text-[0.8rem] font-semibold transition-all spring-click capitalize",
              view === tab
                ? "bg-brand-card text-brand-text-bright shadow-sm"
                : "text-brand-text-dim hover:text-brand-text"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Insight buttons */}
      {view === "messages" && (
        <div className="flex gap-2 w-full md:w-auto flex-wrap overflow-x-auto pb-1 md:pb-0">
          {insightButtons.map(({ type, label, icon: Icon }) => (
            <button
              key={type}
              onClick={() => onInsight(type)}
              disabled={aiLoading}
              className="px-3 py-1.5 rounded-brand-sm border border-brand-accent/30 bg-brand-accent/10 text-brand-accent text-[0.75rem] font-medium hover:bg-brand-accent/20 whitespace-nowrap flex items-center gap-1.5 disabled:opacity-50 spring-click"
            >
              <Icon size={14} /> {label}
            </button>
          ))}
          <button
            onClick={onAnalyze}
            disabled={aiLoading}
            className="px-3 py-1.5 rounded-brand-sm border border-brand-accent/30 bg-brand-accent/10 text-brand-accent text-[0.75rem] font-medium hover:bg-brand-accent/20 whitespace-nowrap flex items-center gap-1.5 disabled:opacity-50 spring-click"
          >
            <Zap size={14} /> Full Analysis
          </button>
        </div>
      )}
    </div>
  );
}
