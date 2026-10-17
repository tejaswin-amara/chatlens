'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { Send, Sparkles } from '@/components/ui/icons';
import { Button } from '@/components/ui/button';
import { triggerHaptic } from '@/lib/fluid-motion';

interface AIChatInputProps {
  onSendMessage: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function AIChatInput({
  onSendMessage,
  disabled = false,
  placeholder = 'Ask AI Copilot about attendance, timetable, marks, fees...',
}: AIChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    triggerHaptic('medium');
    onSendMessage(trimmed);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  return (
    <div className="relative flex items-end gap-2 p-2 bg-surface-2/70 backdrop-blur-xl border border-border rounded-[--radius-xl] shadow-xl focus-within:border-primary/50 transition-all">
      <div className="flex-1 min-w-0">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="w-full resize-none bg-transparent border-0 focus:outline-hidden text-xs text-foreground placeholder:text-muted-foreground max-h-[120px] py-2 px-3 font-normal leading-relaxed"
          aria-label="Ask AI Copilot"
        />
      </div>
      <Button
        size="icon"
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className="rounded-[--radius-lg] bg-primary hover:bg-primary/90 text-primary-foreground shrink-0 w-11 h-11 min-w-[44px] min-h-[44px] flex items-center justify-center transition-all touch-manipulation active:scale-95 cursor-pointer shadow-md"
        aria-label="Send query"
      >
        {disabled ? (
          <Sparkles className="w-4 h-4 animate-spin" />
        ) : (
          <Send className="w-4 h-4" />
        )}
      </Button>
    </div>
  );
}
