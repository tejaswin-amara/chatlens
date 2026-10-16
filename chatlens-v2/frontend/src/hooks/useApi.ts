import { useCallback, useMemo } from "react";
import type { Chat, Message, ChatStats, GlobalStats, SparkStatus } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function fetchJSON<T = unknown>(endpoint: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || body.error || res.statusText);
  }
  return res.json();
}

export function useApi() {
  const loadChats = useCallback(() => fetchJSON<Chat[]>("/api/chats").catch(() => []), []);

  const loadStats = useCallback(
    () => fetchJSON<GlobalStats>("/api/stats").catch(() => ({ total_messages: 0, total_chats: 0 })),
    [],
  );

  const loadGlobalSummary = useCallback(
    () => fetchJSON<{ summary: string }>("/api/global_summarize").then((d) => d.summary),
    [],
  );

  const loadMessages = useCallback(
    (chat: string, limit = 200, skip = 0) =>
      fetchJSON<Message[]>(
        `/api/messages?chat_name=${encodeURIComponent(chat)}&limit=${limit}&skip=${skip}`
      ).catch(() => []),
    [],
  );

  const searchMessages = useCallback(
    (chat: string | null, query: string, sender?: string) => {
      const params = new URLSearchParams();
      if (chat) params.append("chat_name", chat);
      if (query) params.append("query", query);
      if (sender) params.append("sender", sender);
      return fetchJSON<Message[]>(`/api/messages/search?${params.toString()}`).catch(() => []);
    },
    [],
  );

  const deleteChat = useCallback(
    (chat: string) =>
      fetchJSON<{ success: boolean; deleted_count: number }>(`/api/chats/${encodeURIComponent(chat)}`, {
        method: "DELETE",
      }),
    [],
  );

  const loadChatStats = useCallback(
    (chat: string) => fetchJSON<ChatStats>(`/api/chats/${encodeURIComponent(chat)}/stats`).catch(() => null),
    [],
  );

  const runInsight = useCallback(
    (chat: string, type: string) =>
      fetchJSON<{ insight?: string; error?: string }>(`/api/chats/${encodeURIComponent(chat)}/insights`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type }),
      }),
    [],
  );

  const runFullAnalysis = useCallback(
    (chat: string) =>
      fetchJSON<Record<string, string>>("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_name: chat }),
      }),
    [],
  );

  const askQuestion = useCallback(
    (question: string, chatName: string | null) =>
      fetchJSON<{ answer: string }>("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, chat_name: chatName }),
      }).then((d) => d.answer),
    [],
  );

  const uploadFile = useCallback((file: File, platform: "whatsapp" | "telegram") => {
    const formData = new FormData();
    formData.append("file", file);
    const ep = platform === "whatsapp" ? "/api/upload/whatsapp" : "/api/upload/telegram";
    return fetchJSON<{ status: string; task_id?: string; count?: number; error?: string }>(ep, {
      method: "POST",
      body: formData,
    });
  }, []);

  const getTaskStatus = useCallback(
    (taskId: string) =>
      fetchJSON<{ status: string; count?: number; error?: string }>(`/api/tasks/${encodeURIComponent(taskId)}`),
    [],
  );

  const getSparkStatus = useCallback(
    () =>
      fetchJSON<SparkStatus>("/api/spark/status").catch((e) => ({
        status: "error",
        mode: "unknown",
        seen_messages: 0,
        pending: [],
        writes: [],
        error: e.message,
      })),
    [],
  );

  const checkTelegramStatus = useCallback(
    () => fetchJSON<{ authorized: boolean }>("/api/telegram/auth/status"),
    [],
  );

  const sendTelegramCode = useCallback(
    (phone: string) =>
      fetchJSON<{ success: boolean; phone_code_hash: string }>("/api/telegram/auth/send_code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
      }),
    [],
  );

  const verifyTelegramCode = useCallback(
    (phone: string, code: string, phoneCodeHash: string) =>
      fetchJSON<{ success: boolean; count?: number; error?: string }>(
        "/api/telegram/auth/verify",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone, code, phone_code_hash: phoneCodeHash }),
        },
      ),
    [],
  );

  const syncTelegramLive = useCallback(
    () =>
      fetchJSON<{ success: boolean; count?: number; error?: string }>(
        "/api/telegram/auth/sync_live",
        { method: "POST" },
      ),
    [],
  );

  return useMemo(
    () => ({
      loadChats,
      loadStats,
      loadGlobalSummary,
      loadMessages,
      searchMessages,
      deleteChat,
      loadChatStats,
      runInsight,
      runFullAnalysis,
      askQuestion,
      uploadFile,
      getTaskStatus,
      getSparkStatus,
      checkTelegramStatus,
      sendTelegramCode,
      verifyTelegramCode,
      syncTelegramLive,
    }),
    [
      loadChats,
      loadStats,
      loadGlobalSummary,
      loadMessages,
      searchMessages,
      deleteChat,
      loadChatStats,
      runInsight,
      runFullAnalysis,
      askQuestion,
      uploadFile,
      getTaskStatus,
      getSparkStatus,
      checkTelegramStatus,
      sendTelegramCode,
      verifyTelegramCode,
      syncTelegramLive,
    ],
  );
}
