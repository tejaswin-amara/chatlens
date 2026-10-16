"use client";

import { Activity, Sparkles, Flag, List, Zap, Search, Download, Trash2, X } from "lucide-react";
import clsx from "clsx";
import { cleanSenderName } from "@/types";

interface ChatHeaderProps {
  chatName: string;
  view: "messages" | "dashboard";
  onViewChange: (view: "messages" | "dashboard") => void;
  onInsight: (type: string) => void;
  onAnalyze: () => void;
  aiLoading: boolean;
  onToggleSearch?: () => void;
  isSearching?: boolean;
  onExport?: () => void;
  onDeleteChat?: () => void;
  senderFilter?: string | null;
  onClearSenderFilter?: () => void;
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
  onToggleSearch,
  isSearching,
  onExport,
  onDeleteChat,
  senderFilter,
  onClearSenderFilter,
}: ChatHeaderProps) {
  return (
    <div className="p-4 px-6 border-b border-brand-border flex items-center gap-3 bg-gradient-to-b from-brand-accent/5 to-transparent flex-wrap">
      <div className="text-[1.05rem] font-semibold text-brand-text-bright flex items-center gap-2 pl-10 md:pl-0 truncate">
        <span>{chatName}</span>
        {senderFilter && (
          <div className="flex items-center gap-1.5 bg-brand-accent/15 border border-brand-accent/30 text-brand-accent text-xs px-2.5 py-1 rounded-full animate-fade-in font-normal">
            <span>Sender: <strong>{cleanSenderName(senderFilter)}</strong></span>
            {onClearSenderFilter && (
              <button
                onClick={onClearSenderFilter}
                className="hover:text-white transition-colors ml-1 p-0.5 rounded-full hover:bg-brand-accent/20 spring-click"
                title="Clear sender filter"
                aria-label="Clear sender filter"
              >
                <X size={12} />
              </button>
            )}
          </div>
        )}
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

      {/* Action tools */}
      <div className="flex items-center gap-1.5 border-l border-brand-border/60 pl-3">
        {onToggleSearch && view === "messages" && (
          <button
            onClick={onToggleSearch}
            className={clsx(
              "p-2 rounded-brand-sm border text-[0.75rem] transition-colors spring-click",
              isSearching
                ? "bg-brand-accent text-brand-bg border-brand-accent"
                : "border-brand-border bg-brand-card text-brand-text-dim hover:text-brand-text"
            )}
            title="Search messages"
          >
            <Search size={15} />
          </button>
        )}

        {onExport && (
          <button
            onClick={onExport}
            className="p-2 rounded-brand-sm border border-brand-border bg-brand-card text-brand-text-dim hover:text-brand-text text-[0.75rem] transition-colors spring-click"
            title="Export chat transcript"
          >
            <Download size={15} />
          </button>
        )}

        {onDeleteChat && (
          <button
            onClick={onDeleteChat}
            className="p-2 rounded-brand-sm border border-brand-border bg-brand-card text-brand-text-dim hover:text-rose-400 text-[0.75rem] transition-colors spring-click"
            title="Delete chat"
          >
            <Trash2 size={15} />
          </button>
        )}
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
