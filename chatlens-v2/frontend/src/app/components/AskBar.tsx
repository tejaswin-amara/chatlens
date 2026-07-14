"use client";

import { Send } from "lucide-react";

interface AskBarProps {
  value: string;
  onChange: (value: string) => void;
  onAsk: () => void;
  disabled: boolean;
}

export default function AskBar({ value, onChange, onAsk, disabled }: AskBarProps) {
  return (
    <div className="p-3.5 px-6 border-t border-brand-border flex gap-2.5 bg-brand-bg/80 backdrop-blur-md">
      <input
        type="text"
        placeholder="Ask a question about your chats..."
        className="flex-1 px-4 py-2.5 rounded-brand border border-brand-border bg-brand-card text-brand-text text-[0.85rem] outline-none focus:border-brand-border-active transition-colors placeholder-brand-text-dim"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onAsk()}
        disabled={disabled}
      />
      <button
        onClick={onAsk}
        disabled={disabled || !value.trim()}
        className="w-10 h-10 rounded-full bg-brand-accent text-brand-bg flex items-center justify-center hover:brightness-110 disabled:opacity-50 transition-all shrink-0 spring-click"
      >
        <Send size={18} />
      </button>
    </div>
  );
}
