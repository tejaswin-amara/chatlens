"use client";

import { useEffect } from "react";
import { CheckCircle, XCircle, Info, X } from "lucide-react";
import clsx from "clsx";
import type { ToastData } from "../types";

interface ToastProps {
  toasts: ToastData[];
  onDismiss: (id: string) => void;
}

const icons = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
} as const;

const styles = {
  success: "border-brand-accent/30 text-brand-accent",
  error: "border-red-500/30 text-red-400",
  info: "border-blue-400/30 text-blue-400",
} as const;

function ToastItem({ toast, onDismiss }: { toast: ToastData; onDismiss: (id: string) => void }) {
  useEffect(() => {
    const t = setTimeout(() => onDismiss(toast.id), 4000);
    return () => clearTimeout(t);
  }, [toast.id, onDismiss]);

  const Icon = icons[toast.type];

  return (
    <div
      className={clsx(
        "glass-panel flex items-center gap-2.5 px-4 py-3 rounded-brand-sm border animate-fade-in",
        styles[toast.type]
      )}
    >
      <Icon size={16} className="shrink-0" />
      <span className="text-[0.84rem] flex-1 text-brand-text">{toast.message}</span>
      <button onClick={() => onDismiss(toast.id)} className="text-brand-text-dim hover:text-brand-text shrink-0">
        <X size={14} />
      </button>
    </div>
  );
}

export default function Toast({ toasts, onDismiss }: ToastProps) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
