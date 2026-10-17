'use client';

import { useState, useEffect, useCallback } from 'react';
import { Sparkles } from '@/components/ui/icons';
import { useAriaAnnounce } from '@/components/ui/aria-live';
import { AIChatSheet } from './AIChatSheet';
import type { ChatMessage } from './AIChatMessageList';
import { triggerHaptic } from '@/lib/fluid-motion';

export interface AICopilotProps {
  initialOpen?: boolean;
}

export function AICopilot({ initialOpen = false }: AICopilotProps) {
  const [isOpen, setIsOpen] = useState(initialOpen);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<
    'idle' | 'thinking' | 'executing_tool' | 'error'
  >('idle');
  const [activeTool, setActiveTool] = useState<string | undefined>(undefined);

  const { announce } = useAriaAnnounce();

  // Keyboard shortcut listener: Ctrl+Shift+A or Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCmdK = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k';
      const isCtrlShiftA =
        e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'a';

      if (isCmdK || isCtrlShiftA) {
        e.preventDefault();
        triggerHaptic('selection');
        setIsOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSendMessage = useCallback(
    async (queryText: string) => {
      if (
        !queryText.trim() ||
        status === 'thinking' ||
        status === 'executing_tool'
      )
        return;

      triggerHaptic('light');
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: queryText,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setStatus('thinking');
      announce('AI Copilot is thinking...', 'polite');

      try {
        const payloadMessages = [...messages, userMsg].map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const res = await fetch('/api/ai/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: payloadMessages }),
        });

        const data = await res.json();

        if (data.success && data.message) {
          const toolCalls = data.toolCalls as
            | Array<{
                tool: string;
                args: Record<string, unknown>;
                result?: Record<string, unknown>;
              }>
            | undefined;

          if (toolCalls && toolCalls.length > 0) {
            setActiveTool(toolCalls[0].tool);
          }

          const assistantMsg: ChatMessage = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: data.message.content,
            timestamp: new Date(),
            toolCalls,
          };

          setMessages((prev) => [...prev, assistantMsg]);
          setStatus('idle');
          setActiveTool(undefined);
          triggerHaptic('success');
          announce('AI Copilot responded.', 'polite');
        } else {
          throw new Error(data.error || 'Failed to receive AI response');
        }
      } catch (err: unknown) {
        console.error('[AI COPILOT] Error sending message:', err);
        const errorMsgText =
          err instanceof Error ? err.message : 'Connection error';

        const errorMsg: ChatMessage = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `I ran into an error processing your query (${errorMsgText}). Please check your connection or try again.`,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, errorMsg]);
        setStatus('error');
        setActiveTool(undefined);
        triggerHaptic('error');
        announce('AI Copilot encountered an error.', 'assertive');
      }
    },
    [messages, status, announce]
  );

  const handleClearChat = useCallback(() => {
    triggerHaptic('warning');
    setMessages([]);
    setStatus('idle');
    setActiveTool(undefined);
    announce('AI Copilot chat history cleared.', 'polite');
  }, [announce]);

  return (
    <>
      {/* Floating Action Trigger Button (FAB with Apple Spring & Specular Highlight) */}
      <button
        onClick={() => {
          triggerHaptic('selection');
          setIsOpen(true);
        }}
        className="fixed bottom-20 right-4 z-40 group flex items-center gap-2.5 rounded-full bg-primary px-4 py-3 text-primary-foreground shadow-lg shadow-primary/20 transition-transform duration-[--duration-normal] ease-[--ease-spring-default] hover:scale-[1.02] active:scale-95 touch-manipulation lg:bottom-6 lg:right-6"
        aria-label="AI Copilot ⌘K (Ctrl+Shift+A)"
        aria-expanded={isOpen}
      >
        <div className="relative">
          <Sparkles className="h-5 w-5 text-primary-foreground" />
          <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-success" />
        </div>
        <span className="font-semibold text-xs tracking-wide font-heading hidden sm:inline-block">
          AI Copilot
        </span>
        <kbd className="ml-1 hidden items-center gap-0.5 rounded bg-primary-foreground/15 px-1.5 py-0.5 font-mono text-[10px] text-primary-foreground md:inline-flex">
          ⌘K
        </kbd>
      </button>

      {/* Render AIChatSheet directly */}
      <AIChatSheet
        open={isOpen}
        onOpenChange={setIsOpen}
        messages={messages}
        status={status}
        activeTool={activeTool}
        onSendMessage={handleSendMessage}
        onClearChat={handleClearChat}
      />
    </>
  );
}
