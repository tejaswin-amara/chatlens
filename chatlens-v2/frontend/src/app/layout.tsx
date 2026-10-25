import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ChatLens — AI-Powered Chat Analysis",
  description:
    "Analyze your Telegram and WhatsApp conversations with AI. Summaries, sentiment analysis, relationship mapping, and interactive Q&A — all local-first.",
  keywords: ["chat analysis", "telegram", "whatsapp", "AI", "sentiment analysis", "conversation insights"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
