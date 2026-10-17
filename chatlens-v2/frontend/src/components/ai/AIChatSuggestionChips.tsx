'use client';

import {
  Calendar,
  DollarSign,
  Award,
  Target,
  BookOpen,
} from '@/components/ui/icons';
import { triggerHaptic } from '@/lib/fluid-motion';

interface SuggestionChip {
  label: string;
  query: string;
  icon: React.ReactNode;
}

const SUGGESTIONS: SuggestionChip[] = [
  {
    label: 'OS Attendance',
    query: 'What is my attendance in OS?',
    icon: <BookOpen className="w-3.5 h-3.5 text-primary" />,
  },
  {
    label: 'Fee Balance',
    query: 'Show fee breakdown',
    icon: <DollarSign className="w-3.5 h-3.5 text-success" />,
  },
  {
    label: 'Today Schedule',
    query: 'What classes do I have today?',
    icon: <Calendar className="w-3.5 h-3.5 text-primary" />,
  },
  {
    label: 'Target 75%',
    query: 'How many classes can I miss in OS?',
    icon: <Target className="w-3.5 h-3.5 text-warning" />,
  },
  {
    label: 'Predict CGPA',
    query: 'Predict CGPA with upcoming courses',
    icon: <Award className="w-3.5 h-3.5 text-primary" />,
  },
];

interface AIChatSuggestionChipsProps {
  onSelectSuggestion: (query: string) => void;
  disabled?: boolean;
}

export function AIChatSuggestionChips({
  onSelectSuggestion,
  disabled = false,
}: AIChatSuggestionChipsProps) {
  return (
    <div className="flex items-center gap-1.5 overflow-x-auto pb-1 custom-scrollbar scroll-smooth">
      <div className="flex items-center gap-1.5 shrink-0 px-0.5">
        {SUGGESTIONS.map((chip, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => {
              triggerHaptic('selection');
              onSelectSuggestion(chip.query);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-surface-2/60 hover:bg-surface-2 text-foreground border border-border apple-pill transition-all touch-manipulation active:scale-95 disabled:opacity-40 shrink-0 min-h-[44px] cursor-pointer"
          >
            {chip.icon}
            <span>{chip.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
