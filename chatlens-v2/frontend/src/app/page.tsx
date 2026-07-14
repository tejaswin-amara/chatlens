"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Menu, X } from "lucide-react";

import type { Chat, Message, ChatStats, GlobalStats, AiCardData, ToastData } from "./types";
import { useApi } from "./hooks/useApi";

import Sidebar from "./components/Sidebar";
import ChatHeader from "./components/ChatHeader";
import { MessageList } from "./components/MessageList";
import { Dashboard } from "./components/Dashboard";
import ImportModal from "./components/ImportModal";
import AskBar from "./components/AskBar";
import { WelcomePage } from "./components/WelcomePage";
import Toast from "./components/Toast";

export default function Home() {
  // ── Global state ──
  const [chats, setChats] = useState<Chat[]>([]);
  const [globalStats, setGlobalStats] = useState<GlobalStats>({ total_messages: 0, total_chats: 0 });
  const [globalSummary, setGlobalSummary] = useState<string | null>(null);

  // ── Navigation ──
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentChat, setCurrentChat] = useState<string | null>(null);
  const [view, setView] = useState<"messages" | "dashboard">("messages");

  // ── Per-chat data ──
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatStats, setChatStats] = useState<ChatStats | null>(null);
  const [loadingView, setLoadingView] = useState(false);

  // ── AI state ──
  const [aiCards, setAiCards] = useState<AiCardData[]>([]);
  const [aiLoading, setAiLoading] = useState<string | null>(null);
  const [askInput, setAskInput] = useState("");

  // ── Modal ──
  const [modalOpen, setModalOpen] = useState(false);

  // ── Toast ──
  const [toasts, setToasts] = useState<ToastData[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const api = useApi();

  // ── Toast helper ──
  const showToast = useCallback((message: string, type: ToastData["type"]) => {
    setToasts((prev) => [...prev, { id: crypto.randomUUID(), message, type }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // ── Initial data load ──
  useEffect(() => {
    Promise.all([api.loadChats(), api.loadStats()]).then(([c, s]) => {
      setChats(c);
      setGlobalStats(s);
    });
    api.loadGlobalSummary().then(setGlobalSummary).catch((e) => setGlobalSummary(`Error: ${e.message}`));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Scroll to bottom on new content ──
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, aiCards, aiLoading]);

  // ── Load data when chat or view changes ──
  useEffect(() => {
    if (!currentChat) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAiCards([]);
    setLoadingView(true);

    if (view === "messages") {
      api.loadMessages(currentChat).then(setMessages).finally(() => setLoadingView(false));
    } else {
      api.loadChatStats(currentChat).then(setChatStats).finally(() => setLoadingView(false));
    }
  }, [currentChat, view]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── AI actions ──
  const handleInsight = async (type: string) => {
    if (!currentChat) return;
    setAiLoading(`Analyzing ${type.replace("_", " ")}...`);
    try {
      const data = await api.runInsight(currentChat, type);
      setAiCards((prev) => [
        ...prev,
        { label: `Insight: ${type.replace("_", " ").toUpperCase()}`, body: data.insight || data.error || "" },
      ]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setAiCards((prev) => [...prev, { label: "Error", body: msg }]);
    } finally {
      setAiLoading(null);
    }
  };

  const handleAnalyze = async () => {
    if (!currentChat) return;
    setAiLoading("Running full analysis...");
    try {
      const data = await api.runFullAnalysis(currentChat);
      if (data.error) {
        setAiCards((prev) => [...prev, { label: "Error", body: data.error }]);
      } else {
        const sections = ["summary", "sentiment", "topics", "relationships", "timeline"];
        const body = sections
          .filter((s) => data[s])
          .map((s) => `### ${s.charAt(0).toUpperCase() + s.slice(1)}\n${data[s]}`)
          .join("\n\n");
        setAiCards((prev) => [...prev, { label: "Full Analysis", body }]);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setAiCards((prev) => [...prev, { label: "Error", body: msg }]);
    } finally {
      setAiLoading(null);
    }
  };

  const handleAsk = async () => {
    const q = askInput.trim();
    if (!q) return;
    setAskInput("");
    setAiCards((prev) => [...prev, { label: "You", body: q }]);
    setAiLoading("Thinking...");
    try {
      const answer = await api.askQuestion(q, currentChat);
      setAiCards((prev) => [...prev, { label: "Answer", body: answer }]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setAiCards((prev) => [...prev, { label: "Error", body: msg }]);
    } finally {
      setAiLoading(null);
    }
  };

  const handleSelectChat = (name: string) => {
    setCurrentChat(name);
    setView("messages");
  };

  const handleImportComplete = () => {
    Promise.all([api.loadChats(), api.loadStats()]).then(([c, s]) => {
      setChats(c);
      setGlobalStats(s);
    });
  };

  return (
    <div className="flex w-full h-full text-[15px]">
      {/* Mobile sidebar toggle */}
      <button
        className="md:hidden fixed top-3 left-3 z-50 w-9 h-9 flex items-center justify-center rounded-brand-sm border border-brand-border bg-brand-card text-brand-text backdrop-blur-md spring-click"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label="Toggle sidebar"
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      <Sidebar
        chats={chats}
        currentChat={currentChat}
        globalStats={globalStats}
        sidebarOpen={sidebarOpen}
        onSelectChat={handleSelectChat}
        onImportClick={() => setModalOpen(true)}
        onCloseMobile={() => setSidebarOpen(false)}
      />

      <main className="flex-1 flex flex-col min-w-0 bg-brand-bg relative">
        {currentChat ? (
          <>
            <ChatHeader
              chatName={currentChat}
              view={view}
              onViewChange={setView}
              onInsight={handleInsight}
              onAnalyze={handleAnalyze}
              aiLoading={!!aiLoading}
            />

            <div className="flex-1 overflow-y-auto">
              {view === "messages" ? (
                <MessageList
                  messages={messages}
                  loading={loadingView}
                  aiCards={aiCards}
                  aiLoading={aiLoading}
                  messagesEndRef={messagesEndRef}
                />
              ) : (
                <Dashboard chatStats={chatStats} loading={loadingView} />
              )}
            </div>

            {view === "messages" && (
              <AskBar
                value={askInput}
                onChange={setAskInput}
                onAsk={handleAsk}
                disabled={!!aiLoading}
              />
            )}
          </>
        ) : (
          <WelcomePage globalSummary={globalSummary} />
        )}
      </main>

      <ImportModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onImportComplete={handleImportComplete}
        onToast={showToast}
        api={api}
      />

      <Toast toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
