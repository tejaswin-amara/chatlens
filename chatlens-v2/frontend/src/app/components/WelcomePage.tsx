"use client";

import { Sparkles } from "lucide-react";
import { FormatAi } from "./FormatAi";

interface WelcomePageProps {
  globalSummary: string | null;
}

export function WelcomePage({ globalSummary }: WelcomePageProps) {
  return (
    <div className="flex-1 flex items-center justify-center p-6 animate-fade-in">
      <div className="max-w-2xl w-full text-center">
        <div className="text-[3.5rem] mb-4">🔍</div>
        <h1 className="text-3xl font-bold gradient-text mb-2">Welcome to ChatLens</h1>
        <p className="text-brand-text-dim text-sm mb-10">
          Select a chat from the sidebar to explore messages, analytics, and AI insights.
        </p>

        <div className="text-left">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-brand-accent" />
            <h2 className="text-sm font-semibold text-brand-text-bright">
              Global Chat Summary
            </h2>
          </div>

          <div className="glass-panel rounded-brand p-6 relative overflow-hidden">
            {/* Ambient glow overlay */}
            <div
              className="absolute inset-0 rounded-brand bg-brand-accent/10 pointer-events-none"
              style={{ animation: "ambientGlow 8s ease-in-out infinite alternate" }}
            />

            <div className="relative z-10 text-[0.85rem] text-brand-text leading-relaxed">
              {globalSummary === null ? (
                <div className="flex flex-col items-center gap-3 py-4">
                  <div className="w-5 h-5 border-2 border-brand-accent border-t-transparent rounded-full animate-spin-custom" />
                  <div className="w-full space-y-2">
                    <div className="h-2.5 w-full bg-brand-border/50 rounded animate-pulse" />
                    <div className="h-2.5 w-4/5 bg-brand-border/50 rounded animate-pulse" />
                    <div className="h-2.5 w-3/5 bg-brand-border/50 rounded animate-pulse" />
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
