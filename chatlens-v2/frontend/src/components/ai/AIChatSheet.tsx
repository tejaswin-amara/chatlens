'use client';

import { Sparkles, Maximize2, Trash2 } from '@/components/ui/icons';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { AIChatMessageList, ChatMessage } from './AIChatMessageList';
import { AIChatSuggestionChips } from './AIChatSuggestionChips';
import { AIToolExecutionIndicator } from './AIToolExecutionIndicator';
import { AIChatInput } from './AIChatInput';
import { triggerHaptic } from '@/lib/fluid-motion';

export interface AIChatSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  messages: ChatMessage[];
  status: 'idle' | 'thinking' | 'executing_tool' | 'error';
  activeTool?: string;
  onSendMessage: (query: string) => void;
  onClearChat: () => void;
  onToggleDialogMode?: () => void;
}

export function AIChatSheet({
  open,
  onOpenChange,
  messages,
  status,
  activeTool,
  onSendMessage,
  onClearChat,
  onToggleDialogMode,
}: AIChatSheetProps) {
  const isBusy = status === 'thinking' || status === 'executing_tool';

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="h-full w-full flex flex-col p-0 apple-sheet border-l border-border shadow-xl sm:max-w-md"
      >
        {/* Drawer Header */}
        <SheetHeader className="flex flex-row items-center justify-between space-y-0 border-b border-border p-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-[--radius-lg] bg-primary/20 border border-primary/30 flex items-center justify-center text-primary">
              <Sparkles className="w-4.5 h-4.5" />
            </div>
            <div>
              <SheetTitle className="text-base font-semibold text-foreground flex items-center gap-2 tracking-tight">
                <span>AI Copilot</span>
                <Badge
                  variant="outline"
                  className="text-[10px] py-0 px-1.5 font-mono apple-pill"
                >
                  Agentic v1.0
                </Badge>
              </SheetTitle>
              <SheetDescription className="text-xs text-muted-foreground font-normal">
                KL Sync ERP Intelligence
              </SheetDescription>
            </div>
          </div>

          <div className="flex items-center gap-1 mr-8">
            {messages.length > 0 && (
              <button
                onClick={() => {
                  triggerHaptic('warning');
                  onClearChat();
                }}
                title="Clear Chat History"
                className="p-2 rounded-full hover:bg-surface-2 text-muted-foreground hover:text-foreground transition-all min-w-[44px] min-h-[44px] flex items-center justify-center touch-manipulation active:scale-90 cursor-pointer"
                aria-label="Clear chat"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}

            {onToggleDialogMode && (
              <button
                onClick={() => {
                  triggerHaptic('light');
                  onToggleDialogMode();
                }}
                title="Expand to Modal"
                className="p-2 rounded-full hover:bg-surface-2 text-muted-foreground hover:text-foreground transition-all min-w-[44px] min-h-[44px] flex items-center justify-center touch-manipulation active:scale-90 cursor-pointer"
                aria-label="Expand to dialog"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            )}
          </div>
        </SheetHeader>

        {/* Message Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
          <AIChatMessageList
            messages={messages}
            onSelectSuggestion={onSendMessage}
          />
          {isBusy && (
            <AIToolExecutionIndicator status={status} toolName={activeTool} />
          )}
        </div>

        {/* Suggestions & Input Footer */}
        <div className="space-y-2 border-t border-border bg-surface-2/60 p-3">
          <AIChatSuggestionChips
            onSelectSuggestion={onSendMessage}
            disabled={isBusy}
          />
          <AIChatInput onSendMessage={onSendMessage} disabled={isBusy} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
