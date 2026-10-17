'use client';

import {
  Sparkles,
  User,
  AlertTriangle,
  CheckCircle2,
  DollarSign,
  Target,
  Award,
  BookOpen,
} from '@/components/ui/icons';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  toolCalls?: Array<{
    tool: string;
    args: Record<string, unknown>;
    result?: Record<string, unknown>;
  }>;
}

interface AIChatMessageListProps {
  messages: ChatMessage[];
  onSelectSuggestion?: (query: string) => void;
}

export function AIChatMessageList({ messages }: AIChatMessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3 text-muted-foreground">
        <div className="w-12 h-12 rounded-[--radius-xl] bg-primary/15 border border-primary/25 flex items-center justify-center text-primary shadow-lg">
          <Sparkles className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground text-sm font-heading tracking-tight">
            KL Sync AI Copilot
          </h3>
          <p className="text-xs text-muted-foreground/80 max-w-[260px] mt-1 font-normal leading-relaxed">
            Ask natural language questions about your attendance, fees, marks,
            timetable, or target CGPA.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 py-2">
      {messages.map((msg) => {
        const isUser = msg.role === 'user';
        return (
          <div
            key={msg.id}
            className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'} animate-spring-up`}
          >
            {!isUser && (
              <div className="w-7 h-7 rounded-[--radius-md] bg-primary/20 border border-primary/30 flex items-center justify-center text-primary shrink-0 mt-0.5 shadow-xs">
                <Sparkles className="w-4 h-4" />
              </div>
            )}

            <div
              className={`max-w-[85%] rounded-[--radius-2xl] px-4 py-3 text-sm shadow-md transition-all ${
                isUser
                  ? 'bg-primary text-primary-foreground rounded-br-xs font-medium'
                  : 'apple-card border border-border text-foreground rounded-bl-xs font-normal'
              }`}
            >
              {/* Message text content */}
              <div className="whitespace-pre-wrap leading-relaxed tracking-tight">
                {renderFormattedText(msg.content)}
              </div>

              {/* Tool Execution Result Cards */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="mt-3 space-y-2 pt-2 border-t border-border">
                  {msg.toolCalls.map((tc, idx) => (
                    <ToolResultCard key={idx} toolCall={tc} />
                  ))}
                </div>
              )}
            </div>

            {isUser && (
              <div className="w-7 h-7 rounded-[--radius-md] bg-surface-2 border border-border flex items-center justify-center text-foreground shrink-0 mt-0.5 shadow-xs">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function renderFormattedText(text: string) {
  const lines = text.split('\n');
  return lines.map((line, idx) => {
    // Bold parsing
    const parts = line.split(/(\*\*.*?\*\*)/g);
    const lineContent = parts.map((part, pIdx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={pIdx} className="font-semibold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });

    return (
      <span key={idx}>
        {lineContent}
        {idx < lines.length - 1 && <br />}
      </span>
    );
  });
}

function ToolResultCard({
  toolCall,
}: {
  toolCall: {
    tool: string;
    args: Record<string, unknown>;
    result?: Record<string, unknown>;
  };
}) {
  const { tool, result } = toolCall;
  if (!result) return null;

  if (tool === 'getAttendance' && Array.isArray(result.attendance)) {
    const list = result.attendance as Array<{
      'Course Code': string;
      'Course Title': string;
      'Attendance Percentage': string;
      'Attended Hours': string;
      'Conducted Hours': string;
    }>;
    return (
      <div className="p-3 rounded-[--radius-xl] bg-surface-2/60 border border-border space-y-2 text-xs">
        <div className="flex items-center gap-1.5 font-semibold text-foreground font-heading">
          <BookOpen className="w-3.5 h-3.5 text-primary" />
          <span>Attendance Breakdown</span>
        </div>
        <div className="space-y-1.5">
          {list.map((item, i) => {
            const pct = parseFloat(
              String(item['Attendance Percentage'] || '0').replace('%', '')
            );
            const isLow = pct < 75;
            return (
              <div
                key={i}
                className="p-2.5 rounded-[--radius-lg] bg-surface-2/40 border border-border space-y-1.5"
              >
                <div className="flex items-center justify-between text-foreground font-semibold">
                  <span className="truncate max-w-[180px] tracking-tight">
                    {item['Course Title'] || item['Course Code']}
                  </span>
                  <Badge
                    variant={
                      isLow ? 'danger' : pct >= 85 ? 'success' : 'warning'
                    }
                    className="tabular-numbers"
                  >
                    {item['Attendance Percentage']}
                  </Badge>
                </div>
                <Progress value={Math.min(100, pct)} className="h-1.5" />
                <div className="text-[10px] text-muted-foreground tabular-numbers font-medium">
                  Attended: {item['Attended Hours']} / {item['Conducted Hours']}{' '}
                  hours
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (tool === 'getFeeDetails' && result.breakdown) {
    const b = result.breakdown as {
      totalAmount: number;
      totalPaid: number;
      totalPending: number;
      hasPendingDue: boolean;
    };
    return (
      <div className="p-3 rounded-[--radius-xl] bg-surface-2/60 border border-border space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 font-semibold text-foreground font-heading">
            <DollarSign className="w-3.5 h-3.5 text-success" />
            <span>Fee Overview</span>
          </div>
          <Badge
            variant={b.hasPendingDue ? 'danger' : 'success'}
            className="tabular-numbers"
          >
            {b.hasPendingDue
              ? `Pending: ₹${b.totalPending.toLocaleString('en-IN')}`
              : 'All Paid'}
          </Badge>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center pt-1">
          <div className="p-2.5 rounded-[--radius-lg] bg-surface-2/40 border border-border">
            <span className="caption-label text-muted-foreground block mb-0.5">
              Paid Amount
            </span>
            <span className="font-bold text-success font-mono tabular-numbers">
              ₹{b.totalPaid.toLocaleString('en-IN')}
            </span>
          </div>
          <div className="p-2.5 rounded-[--radius-lg] bg-surface-2/40 border border-border">
            <span className="caption-label text-muted-foreground block mb-0.5">
              Total Amount
            </span>
            <span className="font-bold text-foreground font-mono tabular-numbers">
              ₹{b.totalAmount.toLocaleString('en-IN')}
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (
    tool === 'calculateAttendanceTarget' &&
    typeof result.currentPercentage === 'number'
  ) {
    const r = result as {
      currentPercentage: number;
      targetPercent: number;
      classesNeeded: number;
      maxBunkable: number;
      status: string;
    };
    const isBelow = r.status === 'below_target';
    return (
      <div className="p-3 rounded-[--radius-xl] bg-surface-2/60 border border-border space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 font-semibold text-foreground font-heading">
            <Target className="w-3.5 h-3.5 text-warning" />
            <span>Attendance Roadmap</span>
          </div>
          <Badge
            variant={isBelow ? 'danger' : 'success'}
            className="tabular-numbers"
          >
            {isBelow
              ? `Needed: +${r.classesNeeded} classes`
              : `Bunkable: ${r.maxBunkable} classes`}
          </Badge>
        </div>
        <div className="text-[11px] text-muted-foreground">
          {isBelow ? (
            <div className="flex items-center gap-1 text-destructive font-medium">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              <span>
                Attend next {r.classesNeeded} consecutive classes to reach{' '}
                {r.targetPercent}%.
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-success font-medium">
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
              <span>
                You have met the {r.targetPercent}% target. You can skip up to{' '}
                {r.maxBunkable} classes.
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (tool === 'predictCGPA' && typeof result.predictedCGPA === 'number') {
    const r = result as {
      currentCGPA: number;
      predictedCGPA: number;
      gpaDelta: number;
      totalCredits: number;
    };
    return (
      <div className="p-3 rounded-[--radius-xl] bg-surface-2/60 border border-border space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 font-semibold text-foreground font-heading">
            <Award className="w-3.5 h-3.5 text-primary" />
            <span>CGPA Forecast Roadmap</span>
          </div>
          <Badge
            variant={r.gpaDelta >= 0 ? 'success' : 'danger'}
            className="tabular-numbers"
          >
            {r.gpaDelta >= 0 ? `+${r.gpaDelta} GPA` : `${r.gpaDelta} GPA`}
          </Badge>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center pt-1">
          <div className="p-2.5 rounded-[--radius-lg] bg-surface-2/40 border border-border">
            <span className="caption-label text-muted-foreground block mb-0.5">
              Current CGPA
            </span>
            <span className="font-bold text-foreground font-mono tabular-numbers">
              {r.currentCGPA}
            </span>
          </div>
          <div className="p-2.5 rounded-[--radius-lg] bg-surface-2/40 border border-border">
            <span className="caption-label text-muted-foreground block mb-0.5">
              Predicted CGPA
            </span>
            <span className="font-bold text-primary font-mono tabular-numbers">
              {r.predictedCGPA}
            </span>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
