import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

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
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
