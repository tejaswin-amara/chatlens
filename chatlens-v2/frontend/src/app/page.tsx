"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Menu, X, Search } from "lucide-react";

import type { Chat, Message, ChatStats, GlobalStats, AiCardData, ToastData } from "@/types";
import { useApi } from "@/hooks/useApi";

import Sidebar from "@/components/Sidebar";
import ChatHeader from "@/components/ChatHeader";
import { MessageList } from "@/components/MessageList";
import { Dashboard } from "@/components/Dashboard";
import ImportModal from "@/components/ImportModal";
import SparkStatusModal from "@/components/SparkStatusModal";
import AskBar from "@/components/AskBar";
import { WelcomePage } from "@/components/WelcomePage";
import Toast from "@/components/Toast";

const PAGE_SIZE = 100;

export default function Home() {
  // ── Global state ──
  const [chats, setChats] = useState<Chat[]>([]);
  const [globalStats, setGlobalStats] = useState<GlobalStats>({ total_messages: 0, total_chats: 0 });
  const [globalSummary, setGlobalSummary] = useState<string | null>(null);

  // ── Navigation ──
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentChat, setCurrentChat] = useState<string | null>(null);
  const [view, setView] = useState<"messages" | "dashboard">("messages");

  // ── In-Chat Search ──
  const [isSearching, setIsSearching] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Message[] | null>(null);

  // ── Per-chat data & pagination ──
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatStats, setChatStats] = useState<ChatStats | null>(null);
  const [loadingView, setLoadingView] = useState(false);
  const [loadingEarlier, setLoadingEarlier] = useState(false);
  const [hasMore, setHasMore] = useState(true);

  // ── AI state ──
  const [aiCards, setAiCards] = useState<AiCardData[]>([]);
  const [aiLoading, setAiLoading] = useState<string | null>(null);
  const [askInput, setAskInput] = useState("");

  // ── Modals ──
  const [modalOpen, setModalOpen] = useState(false);
  const [sparkModalOpen, setSparkModalOpen] = useState(false);

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

  // ── Scroll to bottom on new content (when not searching) ──
  useEffect(() => {
    if (!isSearching && !searchResults) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, aiCards, aiLoading, isSearching, searchResults]);

  // ── Load data when chat or view changes ──
  useEffect(() => {
    if (!currentChat) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadingView(true);

    if (view === "messages") {
      api.loadMessages(currentChat, PAGE_SIZE, 0).then((msgs) => {
        setMessages(msgs);
        setHasMore(msgs.length === PAGE_SIZE);
      }).finally(() => setLoadingView(false));
    } else {
      api.loadChatStats(currentChat).then(setChatStats).finally(() => setLoadingView(false));
    }
  }, [currentChat, view]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Pagination: Load earlier messages ──
  const handleLoadEarlier = async () => {
    if (!currentChat || loadingEarlier) return;
    setLoadingEarlier(true);
    try {
      const older = await api.loadMessages(currentChat, PAGE_SIZE, messages.length);
      if (older.length < PAGE_SIZE) {
        setHasMore(false);
      }
      setMessages((prev) => [...older, ...prev]);
    } catch {
      showToast("Failed to load earlier messages", "error");
    } finally {
      setLoadingEarlier(false);
    }
  };

  // ── In-Chat Message Search ──
  const handleSearchSubmit = async () => {
    const q = searchQuery.trim();
    if (!q || !currentChat) {
      setSearchResults(null);
      return;
    }
    setLoadingView(true);
    try {
      const results = await api.searchMessages(currentChat, q);
      setSearchResults(results);
    } catch {
      showToast("Message search failed", "error");
    } finally {
      setLoadingView(false);
    }
  };

  // ── Delete Chat ──
  const handleDeleteChat = async () => {
    if (!currentChat) return;
    const confirmed = window.confirm(`Are you sure you want to delete all messages in "${currentChat}"?`);
    if (!confirmed) return;

    try {
      await api.deleteChat(currentChat);
      showToast(`Deleted chat "${currentChat}"`, "success");
      setCurrentChat(null);
      Promise.all([api.loadChats(), api.loadStats()]).then(([c, s]) => {
        setChats(c);
        setGlobalStats(s);
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to delete chat";
      showToast(msg, "error");
    }
  };

  // ── Export Chat as Markdown ──
  const handleExport = () => {
    if (!currentChat || messages.length === 0) {
      showToast("No messages to export", "info");
      return;
    }
    const lines = [
      `# Chat Transcript: ${currentChat}`,
      `*Exported from ChatLens on ${new Date().toISOString()}*`,
      "",
      "---",
      "",
    ];
    for (const m of messages) {
      lines.push(`**${m.sender}** (${m.timestamp}):\n${m.text}\n`);
    }
    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${currentChat.replace(/[^a-zA-Z0-9_-]/g, "_")}_transcript.md`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Transcript exported to Markdown", "success");
  };

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
    setAiLoading("Thinking with semantic retrieval...");
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
    setAiCards([]);
    setIsSearching(false);
    setSearchQuery("");
    setSearchResults(null);
    setHasMore(true);
  };

  const handleImportComplete = () => {
    Promise.all([api.loadChats(), api.loadStats()]).then(([c, s]) => {
      setChats(c);
      setGlobalStats(s);
    });
  };

  const displayedMessages = searchResults ?? messages;

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
        onSparkClick={() => setSparkModalOpen(true)}
        onCloseMobile={() => setSidebarOpen(false)}
      />

      {/* Mobile sidebar backdrop overlay */}
      {sidebarOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-30 transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

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
              onToggleSearch={() => {
                setIsSearching(!isSearching);
                if (isSearching) {
                  setSearchResults(null);
                  setSearchQuery("");
                }
              }}
              isSearching={isSearching}
              onExport={handleExport}
              onDeleteChat={handleDeleteChat}
            />

            {/* In-chat search banner */}
            {isSearching && view === "messages" && (
              <div className="p-3 px-6 bg-brand-card border-b border-brand-border flex items-center gap-2 animate-fade-in">
                <Search size={14} className="text-brand-accent shrink-0" />
                <input
                  type="text"
                  placeholder="Filter messages in this chat (press Enter)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearchSubmit()}
                  className="flex-1 bg-transparent border-none text-[0.82rem] text-brand-text outline-none placeholder-brand-text-dim"
                  autoFocus
                />
                {searchResults && (
                  <button
                    onClick={() => {
                      setSearchResults(null);
                      setSearchQuery("");
                    }}
                    className="text-[0.7rem] text-brand-text-dim hover:text-brand-text px-2 py-0.5 rounded border border-brand-border"
                  >
                    Clear Filter ({searchResults.length} found)
                  </button>
                )}
              </div>
            )}

            <div className="flex-1 overflow-y-auto">
              {view === "messages" ? (
                <MessageList
                  messages={displayedMessages}
                  loading={loadingView}
                  aiCards={aiCards}
                  aiLoading={aiLoading}
                  messagesEndRef={messagesEndRef}
                  onLoadEarlier={handleLoadEarlier}
                  hasMore={hasMore && !searchResults}
                  loadingEarlier={loadingEarlier}
                  searchQuery={searchResults ? searchQuery : undefined}
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

      <SparkStatusModal
        open={sparkModalOpen}
        onClose={() => setSparkModalOpen(false)}
        onRefresh={api.getSparkStatus}
      />

      <Toast toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
