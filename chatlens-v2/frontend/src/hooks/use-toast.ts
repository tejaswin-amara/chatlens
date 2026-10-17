'use client';

import * as React from 'react';

export interface ToastItem {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  variant?: 'default' | 'destructive' | 'success' | 'info' | 'warning';
  duration?: number;
  action?: React.ReactNode;
}

let toasts: ToastItem[] = [];
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

export function dismiss(toastId?: string) {
  toasts = toastId ? toasts.filter((t) => t.id !== toastId) : [];
  notify();
}

export function toast(props: Omit<ToastItem, 'id'>) {
  const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
  const item: ToastItem = { ...props, id, duration: props.duration ?? 4000 };
  toasts = [item, ...toasts].slice(0, 5);
  notify();

  if (item.duration && item.duration > 0) {
    setTimeout(() => dismiss(id), item.duration);
  }

  return { id, dismiss: () => dismiss(id) };
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot() {
  return toasts;
}

export function useToast() {
  const activeToasts = React.useSyncExternalStore(
    subscribe,
    getSnapshot,
    getSnapshot
  );
  return {
    toasts: activeToasts,
    toast,
    dismiss,
  };
}
