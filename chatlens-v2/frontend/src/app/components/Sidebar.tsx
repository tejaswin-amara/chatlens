"use client";

import { useState } from "react";
import { Search, Plus, MessageSquare } from "lucide-react";
import clsx from "clsx";
import type { Chat } from "../types";

interface SidebarProps {
  chats: Chat[];
  currentChat: string | null;
  globalStats: { total_messages: number; total_chats: number };
  sidebarOpen: boolean;
  onSelectChat: (name: string) => void;
  onImportClick: () => void;
  onCloseMobile: () => void;
}

export default function Sidebar({
  chats,
  currentChat,
  globalStats,
  sidebarOpen,
  onSelectChat,
  onImportClick,
  onCloseMobile,
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filtered = searchQuery
    ? chats.filter((c) => c.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : chats;

  return (
    <aside
      className={clsx(
        "w-[300px] min-w-[260px] border-r border-brand-border flex flex-col bg-brand-bg/60 backdrop-blur-xl transition-all duration-300 z-40",
        "md:static absolute top-0 bottom-0",
        sidebarOpen ? "left-0" : "-left-[300px] md:left-0"
      )}
    >
      {/* Branding + Stats */}
      <div className="p-6 pb-4 border-b border-brand-border">
        <div className="text-[1.4rem] font-bold text-brand-text-bright flex items-center gap-2">
          <Search className="text-brand-accent" size={24} />
          <span className="bg-gradient-to-br from-brand-accent to-[#00b4d8] bg-clip-text text-transparent">
            ChatLens
          </span>
        </div>
        <div className="text-[0.75rem] text-brand-text-dim mt-2">
          {globalStats.total_messages.toLocaleString()} messages · {globalStats.total_chats} chats
        </div>
        <button
          onClick={() => {
            onImportClick();
            onCloseMobile();
          }}
          className="w-full mt-3 px-4 py-2 rounded-brand-sm border border-brand-accent/30 bg-brand-accent/10 text-brand-accent text-[0.78rem] font-medium hover:bg-brand-accent/20 transition-colors flex items-center justify-center gap-2 spring-click"
        >
          <Plus size={16} /> Import Data
        </button>
      </div>

      {/* Search */}
      <div className="px-3 pt-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-text-dim" />
          <input
            type="text"
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-2 rounded-brand-sm border border-brand-border bg-brand-card text-[0.8rem] text-brand-text outline-none focus:border-brand-border-active transition-colors placeholder-brand-text-dim"
          />
        </div>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {filtered.length === 0 ? (
          <div className="text-center p-10 text-brand-text-dim text-[0.85rem] leading-relaxed flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-brand-card flex items-center justify-center text-brand-text-dim opacity-50">
              <MessageSquare size={20} />
            </div>
            {chats.length === 0
              ? <>No chats imported yet.<br />Use the button above to import.</>
              : "No chats match your search."}
          </div>
        ) : (
          filtered.map((c, i) => (
            <div
              key={c.name}
              onClick={() => {
                onSelectChat(c.name);
                onCloseMobile();
              }}
              style={{ animationDelay: `${i * 50}ms` }}
              className={clsx(
                "opacity-0 animate-fade-up-stagger p-3 rounded-brand-sm cursor-pointer transition-colors flex items-center gap-2.5 border",
                currentChat === c.name
                  ? "bg-brand-accent-glow border-brand-border-active"
                  : "border-transparent hover:bg-brand-card-hover"
              )}
            >
              <span
                className={clsx(
                  "text-[0.6rem] font-semibold px-1.5 py-0.5 rounded shrink-0 uppercase tracking-wide",
                  c.platform === "whatsapp"
                    ? "bg-brand-whatsapp/15 text-brand-whatsapp"
                    : "bg-brand-telegram/15 text-brand-telegram"
                )}
              >
                {c.platform === "whatsapp" ? "WA" : "TG"}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[0.85rem] font-medium text-brand-text-bright truncate">{c.name}</div>
                <div className="text-[0.7rem] text-brand-text-dim mt-0.5">
                  {c.message_count.toLocaleString()} msgs
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
