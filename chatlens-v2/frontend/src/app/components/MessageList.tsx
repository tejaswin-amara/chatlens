"use client";

import clsx from "clsx";
import type { Message } from "../types";
import { cleanSenderName } from "../types";
import { AiCard } from "./AiCard";

interface MessageListProps {
  messages: Message[];
  loading: boolean;
  aiCards: { label: string; body: string }[];
  aiLoading: string | null;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
}

const SKELETON_WIDTHS = ["w-3/4", "w-2/3", "w-1/2", "w-2/3", "w-3/4", "w-1/2"];

function formatDate(ts: string) {
  const d = new Date(ts);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatTime(ts: string) {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function isSameDay(a: string, b: string) {
  const da = new Date(a);
  const db = new Date(b);
  return da.getFullYear() === db.getFullYear() && da.getMonth() === db.getMonth() && da.getDate() === db.getDate();
}

function isGrouped(prev: Message, curr: Message) {
  if (prev.sender !== curr.sender) return false;
  const diff = Math.abs(new Date(curr.timestamp).getTime() - new Date(prev.timestamp).getTime());
  return diff < 2 * 60 * 1000;
}

export function MessageList({ messages, loading, aiCards, aiLoading, messagesEndRef }: MessageListProps) {
  if (loading) {
    return (
      <div className="flex flex-col gap-3 p-4">
        {SKELETON_WIDTHS.map((w, i) => (
          <div
            key={i}
            className={clsx(
              "rounded-brand p-4 bg-brand-border/50 animate-pulse",
              w,
              i % 2 === 0 ? "self-start" : "self-end"
            )}
          >
            <div className="h-2.5 w-16 bg-white/10 rounded mb-2" />
            <div className="h-2 w-full bg-white/10 rounded mb-1.5" />
            <div className="h-2 w-4/5 bg-white/10 rounded" />
          </div>
        ))}
      </div>
    );
  }

  // Find if there is any message sent by the main user (Prudhvi) in this message list
  const hasUser = messages.some(msg => {
    const s = msg.sender.toLowerCase();
    return s.includes("prudhvi") || s.includes("2520030286");
  });

  // Determine the first sender to assign left alignment (if no user present)
  const firstSender = messages.length > 0 ? messages[0].sender : null;

  return (
    <div className="flex flex-col gap-0.5 p-4">
      {messages.map((msg, i) => {
        const prev = i > 0 ? messages[i - 1] : null;
        const showDate = !prev || !isSameDay(prev.timestamp, msg.timestamp);
        const grouped = prev ? isGrouped(prev, msg) : false;

        let isLeft = true;
        if (hasUser) {
          const s = msg.sender.toLowerCase();
          isLeft = !(s.includes("prudhvi") || s.includes("2520030286"));
        } else {
          isLeft = msg.sender === firstSender;
        }

        return (
          <div key={i} className="animate-fade-in">
            {showDate && (
              <div className="flex items-center gap-3 my-4">
                <div className="flex-1 h-px bg-brand-border" />
                <span className="text-[0.7rem] text-brand-text-dim shrink-0">
                  {formatDate(msg.timestamp)}
                </span>
                <div className="flex-1 h-px bg-brand-border" />
              </div>
            )}
            <div
              className={clsx(
                "flex flex-col max-w-[85%]",
                grouped ? "mt-0.5" : "mt-2",
                isLeft ? "self-start items-start" : "self-end items-end"
              )}
            >
              {!grouped && (
                <span
                  className={clsx(
                    "text-[0.7rem] font-medium mb-0.5 px-1",
                    isLeft ? "text-brand-text-dim" : "text-brand-accent"
                  )}
                >
                  {cleanSenderName(msg.sender)}
                </span>
              )}
              <div
                className={clsx(
                  "rounded-brand-sm px-3 py-2 text-[0.85rem] leading-relaxed border",
                  isLeft
                    ? "bg-brand-card border-brand-border text-brand-text"
                    : "bg-brand-accent/10 border-brand-accent/15 text-brand-text"
                )}
              >
                <span>{msg.text}</span>
                <span className="text-[0.6rem] text-brand-text-dim ml-2 whitespace-nowrap">
                  {formatTime(msg.timestamp)}
                </span>
              </div>
            </div>
          </div>
        );
      })}

      {aiCards.map((card, i) => (
        <div key={`ai-${i}`} className="animate-fade-in mt-2">
          <AiCard label={card.label} body={card.body} />
        </div>
      ))}

      {aiLoading && (
        <div className="glass-panel rounded-brand p-5 my-2 animate-fade-in">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-3.5 h-3.5 border-2 border-brand-accent border-t-transparent rounded-full animate-spin-custom" />
            <span className="text-[0.7rem] font-semibold uppercase tracking-wider text-brand-accent">
              {aiLoading}
            </span>
          </div>
          <div className="space-y-2">
            <div className="h-2.5 w-full bg-brand-border/50 rounded animate-pulse" />
            <div className="h-2.5 w-4/5 bg-brand-border/50 rounded animate-pulse" />
            <div className="h-2.5 w-3/5 bg-brand-border/50 rounded animate-pulse" />
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
