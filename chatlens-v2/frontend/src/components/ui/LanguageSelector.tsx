'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useI18n, SUPPORTED_LANGUAGES } from '@/lib/i18n';
import { Globe, Check } from '@/components/ui/icons';
import { triggerHaptic } from '@/lib/fluid-motion';

export function LanguageSelector({ className = '' }: { className?: string }) {
  const { locale, changeLocale, currentLanguage } = useI18n();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      )
        setOpen(false);
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className={`relative inline-block ${className}`} ref={containerRef}>
      <button
        type="button"
        onClick={() => {
          triggerHaptic('light');
          setOpen((current) => !current);
        }}
        className="flex min-h-[44px] min-w-[44px] items-center gap-1.5 rounded-full border border-border bg-surface-1/80 px-2.5 py-1.5 text-xs font-medium text-foreground shadow-xs transition-colors hover:bg-surface-2"
        aria-label="Change language"
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <Globe className="h-4 w-4 text-primary" />
        <span className="hidden sm:inline">{currentLanguage.flag}</span>
        <span className="text-[11px] font-semibold uppercase tracking-wider">
          {currentLanguage.code}
        </span>
      </button>

      {open && (
        <div
          className="absolute end-0 top-full z-50 mt-2 w-48 overflow-hidden rounded-[--radius-lg] border border-border bg-surface-1/95 p-1 shadow-xl backdrop-blur-xl animate-spring-up"
          role="listbox"
          aria-label="Available languages"
        >
          {SUPPORTED_LANGUAGES.map((lang) => {
            const selected = locale === lang.code;
            return (
              <button
                key={lang.code}
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => {
                  triggerHaptic('selection');
                  changeLocale(lang.code);
                  setOpen(false);
                }}
                className={`flex min-h-[44px] w-full items-center justify-between rounded-[--radius-md] px-3 py-2 text-left text-xs transition-colors ${selected ? 'bg-primary/15 font-semibold text-primary' : 'text-muted-foreground hover:bg-surface-2 hover:text-foreground'}`}
              >
                <span className="flex items-center gap-2">
                  <span className="text-sm">{lang.flag}</span>
                  <span>{lang.nativeName}</span>
                </span>
                {selected && <Check className="h-3.5 w-3.5 text-primary" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
