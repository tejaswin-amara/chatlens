"use client";

import clsx from "clsx";
import { FormatAi } from "./FormatAi";

interface AiCardProps {
  label: string;
  body: string;
}

export function AiCard({ label, body }: AiCardProps) {
  const isSelf = label === "You";

  return (
    <div
      className={clsx(
        "glass-panel rounded-brand p-5 my-2 animate-fade-in",
        isSelf
          ? "self-end max-w-[75%] border-brand-accent/30"
          : "w-full"
      )}
    >
      <div className="flex items-center gap-2 mb-2">
        {!isSelf && (
          <span className="text-brand-accent text-xs">✦</span>
        )}
        <span className="text-[0.7rem] font-semibold uppercase tracking-wider text-brand-accent">
          {label}
        </span>
      </div>
      <div className="text-[0.85rem] text-brand-text leading-relaxed">
        <FormatAi text={body} />
      </div>
    </div>
  );
}
