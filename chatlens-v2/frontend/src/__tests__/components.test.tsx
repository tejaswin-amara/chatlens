import { describe, it, expect, vi } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import AskBar from "../components/AskBar";
import ChatHeader from "../components/ChatHeader";
import { MessageList } from "../components/MessageList";
import Toast from "../components/Toast";
import { WelcomePage } from "../components/WelcomePage";
import { AiCard } from "../components/AiCard";
import { FormatAi } from "../components/FormatAi";
import Sidebar from "../components/Sidebar";
import { Dashboard } from "../components/Dashboard";
import ImportModal from "../components/ImportModal";
import SparkStatusModal from "../components/SparkStatusModal";
import { cleanSenderName } from "../types";
import type { ChatStats } from "../types";

// Mock chart.js / react-chartjs-2 for Node SSR test environment
vi.mock("react-chartjs-2", () => ({
  Bar: () => <div data-testid="mock-bar-chart">Mock Bar Chart</div>,
}));

describe("Frontend Component Suite (SSR Markup & Accessibility)", () => {
  describe("types.cleanSenderName", () => {
    it("strips leading phone numbers or roll prefixes", () => {
      expect(cleanSenderName("2520030286 Alice")).toBe("Alice");
      expect(cleanSenderName("+91 9876543210 Bob")).toBe("Bob");
      expect(cleanSenderName("prudhvi sai kari")).toBe("Prudhvi Sai Kari");
    });
  });

  describe("AskBar", () => {
    it("renders input and send button with correct aria-labels and states", () => {
      const html = renderToStaticMarkup(
        <AskBar value="What was the homework?" onChange={vi.fn()} onAsk={vi.fn()} disabled={false} />
      );
      expect(html).toContain('aria-label="Ask a question about your chats"');
      expect(html).toContain('aria-label="Send question"');
      expect(html).toContain('value="What was the homework?"');
      // Button should NOT have the disabled attribute
      expect(html).not.toMatch(/<button[^>]*\sdisabled[=>\s]/);
    });

    it("renders disabled button when value is empty", () => {
      const html = renderToStaticMarkup(
        <AskBar value="" onChange={vi.fn()} onAsk={vi.fn()} disabled={false} />
      );
      expect(html).toMatch(/<button[^>]*\sdisabled/);
    });
  });

  describe("ChatHeader", () => {
    it("renders chat title, tab switchers, and action buttons", () => {
      const html = renderToStaticMarkup(
        <ChatHeader
          chatName="CSE-2026 Study Group"
          view="messages"
          onViewChange={vi.fn()}
          onInsight={vi.fn()}
          onAnalyze={vi.fn()}
          aiLoading={false}
          onToggleSearch={vi.fn()}
          isSearching={false}
          onExport={vi.fn()}
          onExportJson={vi.fn()}
          onExportCsv={vi.fn()}
          onDeleteChat={vi.fn()}
          senderFilter="Bob"
          onClearSenderFilter={vi.fn()}
        />
      );

      expect(html).toContain("CSE-2026 Study Group");
      expect(html).toContain("Sender:");
      expect(html).toContain("Bob");
      expect(html).toContain('aria-label="Clear sender filter"');
      expect(html).toContain('aria-label="Search messages"');
      expect(html).toContain('aria-label="Export chat transcript (Markdown)"');
      expect(html).toContain('aria-label="Export chat as JSON"');
      expect(html).toContain('aria-label="Export chat as CSV"');
      expect(html).toContain('aria-label="Delete chat"');
      expect(html).toContain("Dynamics");
      expect(html).toContain("Full Analysis");
    });
  });

  describe("MessageList", () => {
    it("renders skeleton placeholders when loading", () => {
      const ref = React.createRef<HTMLDivElement>();
      const html = renderToStaticMarkup(
        <MessageList
          messages={[]}
          loading={true}
          aiCards={[]}
          aiLoading={null}
          messagesEndRef={ref}
        />
      );
      expect(html).toContain("animate-pulse");
    });

    it("renders empty state message when list is empty", () => {
      const ref = React.createRef<HTMLDivElement>();
      const html = renderToStaticMarkup(
        <MessageList
          messages={[]}
          loading={false}
          aiCards={[]}
          aiLoading={null}
          messagesEndRef={ref}
        />
      );
      expect(html).toContain("No messages in this chat.");
    });

    it("renders messages with timestamps and formatted senders", () => {
      const ref = React.createRef<HTMLDivElement>();
      const msgs = [
        { sender: "Alice", text: "Hello there!", timestamp: "2026-10-15T10:00:00Z" },
        { sender: "Bob", text: "Hi Alice!", timestamp: "2026-10-15T10:05:00Z" },
      ];
      const html = renderToStaticMarkup(
        <MessageList
          messages={msgs}
          loading={false}
          aiCards={[]}
          aiLoading={null}
          messagesEndRef={ref}
        />
      );
      expect(html).toContain("Alice");
      expect(html).toContain("Hello there!");
      expect(html).toContain("Bob");
      expect(html).toContain("Hi Alice!");
    });
  });

  describe("Sidebar", () => {
    it("renders branding, stats, and search bar with proper accessibility attributes", () => {
      const chats = [
        { name: "Group A", platform: "whatsapp", message_count: 150 },
        { name: "Group B", platform: "telegram", message_count: 320 },
      ];
      const stats = { total_messages: 470, total_chats: 2 };
      const html = renderToStaticMarkup(
        <Sidebar
          chats={chats}
          currentChat="Group A"
          globalStats={stats}
          sidebarOpen={true}
          onSelectChat={vi.fn()}
          onImportClick={vi.fn()}
          onSparkClick={vi.fn()}
          onCloseMobile={vi.fn()}
        />
      );

      expect(html).toContain("ChatLens");
      expect(html).toContain("470 messages · 2 chats");
      expect(html).toContain('aria-label="Search chats"');
      expect(html).toContain("Group A");
      expect(html).toContain("Group B");
      expect(html).toContain("WA");
      expect(html).toContain("TG");
    });
  });

  describe("Dashboard", () => {
    it("renders loading skeleton cards when loading", () => {
      const html = renderToStaticMarkup(
        <Dashboard chatStats={null} loading={true} onFilterSender={vi.fn()} />
      );
      expect(html).toContain("animate-pulse");
    });

    it("renders aggregated metrics and top contributors with filter buttons", () => {
      const sampleStats: ChatStats = {
        total_messages: 1000,
        total_words: 8500,
        awards: { "Night Owl": "Charlie" },
        top_senders: [
          { name: "Alice", count: 600 },
          { name: "Bob", count: 400 },
        ],
        activity_by_hour: { "10": 200, "14": 500 },
        activity_by_day: { Mon: 300, Fri: 700 },
      };

      const html = renderToStaticMarkup(
        <Dashboard chatStats={sampleStats} loading={false} onFilterSender={vi.fn()} />
      );

      expect(html).toContain("1,000");
      expect(html).toContain("8,500");
      expect(html).toContain("Night Owl");
      expect(html).toContain("Charlie");
      expect(html).toContain("Alice");
      expect(html).toContain('aria-label="Filter messages by Alice"');
      expect(html).toContain('aria-label="Filter messages by Bob"');
    });
  });

  describe("ImportModal", () => {
    it("returns null when open is false", () => {
      const api = {
        uploadFile: vi.fn(),
        getTaskStatus: vi.fn(),
        checkTelegramStatus: vi.fn(),
        sendTelegramCode: vi.fn(),
        verifyTelegramCode: vi.fn(),
        syncTelegramLive: vi.fn(),
      };
      const html = renderToStaticMarkup(
        <ImportModal
          open={false}
          onClose={vi.fn()}
          onImportComplete={vi.fn()}
          onToast={vi.fn()}
          api={api}
        />
      );
      expect(html).toBe("");
    });

    it("renders modal dialog with tabs, upload area, and accessible close button", () => {
      const api = {
        uploadFile: vi.fn(),
        getTaskStatus: vi.fn(),
        checkTelegramStatus: vi.fn(),
        sendTelegramCode: vi.fn(),
        verifyTelegramCode: vi.fn(),
        syncTelegramLive: vi.fn(),
      };
      const html = renderToStaticMarkup(
        <ImportModal
          open={true}
          onClose={vi.fn()}
          onImportComplete={vi.fn()}
          onToast={vi.fn()}
          api={api}
        />
      );
      expect(html).toContain("Import Data");
      expect(html).toContain('aria-label="Close dialog"');
      expect(html).toContain("File Upload");
      expect(html).toContain("Telegram Live");
      expect(html).toContain("Click or drag file here");
    });
  });

  describe("SparkStatusModal", () => {
    it("returns null when open is false", () => {
      const html = renderToStaticMarkup(
        <SparkStatusModal open={false} onClose={vi.fn()} onRefresh={vi.fn()} />
      );
      expect(html).toBe("");
    });

    it("renders modal header with accessible buttons when open", () => {
      const html = renderToStaticMarkup(
        <SparkStatusModal open={true} onClose={vi.fn()} onRefresh={vi.fn()} />
      );
      expect(html).toContain("SPARK Personal Assistant Daemon");
      expect(html).toContain('aria-label="Refresh status"');
      expect(html).toContain('aria-label="Close dialog"');
    });
  });

  describe("Toast", () => {
    it("renders null when toasts array is empty", () => {
      const html = renderToStaticMarkup(<Toast toasts={[]} onDismiss={vi.fn()} />);
      expect(html).toBe("");
    });

    it("renders toast notifications with message and dismiss button aria-label", () => {
      const toasts = [
        { id: "1", message: "Import completed successfully", type: "success" as const },
        { id: "2", message: "Failed to parse file", type: "error" as const },
      ];
      const html = renderToStaticMarkup(<Toast toasts={toasts} onDismiss={vi.fn()} />);
      expect(html).toContain("Import completed successfully");
      expect(html).toContain("Failed to parse file");
      expect(html).toContain('aria-label="Dismiss notification"');
    });
  });

  describe("WelcomePage & AiCard", () => {
    it("renders WelcomePage with heading and summary", () => {
      const html = renderToStaticMarkup(
        <WelcomePage globalSummary="This is a summary of all recent academic chats." />
      );
      expect(html).toContain("Welcome to ChatLens");
      expect(html).toContain("Global Chat Summary");
      expect(html).toContain("This is a summary of all recent academic chats.");
    });

    it("renders AiCard with label and markdown formatted body", () => {
      const html = renderToStaticMarkup(
        <AiCard label="Relationship Dynamics" body="**Strong collaboration** observed between members." />
      );
      expect(html).toContain("Relationship Dynamics");
      expect(html).toContain("Strong collaboration");
    });
  });

  describe("FormatAi", () => {
    it("renders bold text and bullet points properly", () => {
      const markdown = "- Point 1: **important**\n- Point 2: *normal*";
      const html = renderToStaticMarkup(<FormatAi text={markdown} />);
      expect(html).toContain("<strong>important</strong>");
      expect(html).toContain("Point 1:");
    });
  });
});
