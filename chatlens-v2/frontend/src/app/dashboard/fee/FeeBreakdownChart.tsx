'use client';

import * as React from 'react';

export interface FeeBreakdownChartProps {
  data: Record<string, unknown>[];
  totalFee?: number;
  pendingFee?: number;
}

export function FeeBreakdownChart({
  data,
  totalFee: propTotal,
  pendingFee: propPending,
}: FeeBreakdownChartProps) {
  let paid = 0;
  let pending = propPending ?? 0;
  let total = propTotal ?? 0;

  if (data && data.length > 0) {
    let calcTotal = 0;
    let calcPending = 0;

    data.forEach((row) => {
      let amount = 0;
      let status = '';

      for (const [key, val] of Object.entries(row)) {
        const k = key.toLowerCase();
        if (
          k.includes('amount') ||
          k.includes('fee') ||
          k.includes('total') ||
          k.includes('payable')
        ) {
          const num = parseFloat(String(val).replace(/[^0-9.]/g, ''));
          if (!isNaN(num) && num > amount) amount = num;
        }
        if (
          k.includes('status') ||
          k.includes('paid') ||
          k.includes('due') ||
          k.includes('balance')
        ) {
          status = String(val).toLowerCase();
        }
      }

      calcTotal += amount;
      if (
        status.includes('unpaid') ||
        status.includes('due') ||
        status.includes('pending') ||
        (status.includes('0') && !status.includes('paid'))
      ) {
        calcPending += amount;
      }
    });

    if (calcTotal > 0) {
      total = calcTotal;
      pending = calcPending;
    }
  }

  paid = Math.max(0, total - pending);
  const paidPct = total > 0 ? Math.round((paid / total) * 100) : 100;
  const pendingPct = 100 - paidPct;

  // Donut chart calculations
  const size = 160;
  const strokeWidth = 18;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const paidDash = (paidPct / 100) * circumference;
  const pendingDash = circumference - paidDash;

  return (
    <div className="rounded-[--radius-2xl] border border-border apple-card p-6 space-y-4 shadow-xl overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground font-heading tracking-tight">
            Fee Summary
          </h3>
          <p className="text-xs text-muted-foreground/80 font-normal">
            Payment distribution status
          </p>
        </div>
        <div className="text-xs font-mono font-bold text-success bg-success/10 border border-success/20 px-2.5 py-1 rounded-full apple-pill">
          {paidPct}% Paid
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-center gap-6 justify-around pt-2">
        {/* SVG Donut */}
        <div className="relative flex items-center justify-center">
          <svg
            width={size}
            height={size}
            viewBox={`0 0 ${size} ${size}`}
            className="transform -rotate-90"
          >
            {/* Background ring */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="rgba(255, 255, 255, 0.10)"
              strokeWidth={strokeWidth}
            />
            {/* Paid Arc */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="var(--success)"
              strokeWidth={strokeWidth}
              strokeDasharray={`${paidDash} ${circumference}`}
              strokeLinecap="round"
              className="transition-all duration-500"
            />
            {/* Pending Arc */}
            {pendingPct > 0 && (
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke="var(--error)"
                strokeWidth={strokeWidth}
                strokeDasharray={`${pendingDash} ${circumference}`}
                strokeDashoffset={-paidDash}
                strokeLinecap="round"
                className="transition-all duration-500"
              />
            )}
          </svg>
          <div className="absolute flex flex-col items-center justify-center text-center">
            <span className="caption-label text-muted-foreground">Total</span>
            <span className="text-sm font-bold text-foreground font-mono tabular-numbers mt-0.5">
              ₹{total.toLocaleString()}
            </span>
          </div>
        </div>

        {/* Legend stats */}
        <div className="space-y-3 w-full sm:w-auto">
          <div className="flex items-center justify-between sm:justify-start gap-4 p-3 rounded-[--radius-lg] bg-surface-2/40 border border-border">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-success inline-block shadow-xs" />
              <span className="text-xs font-semibold text-muted-foreground">
                Paid Amount
              </span>
            </div>
            <span className="text-xs font-bold text-success font-mono tabular-numbers">
              ₹{paid.toLocaleString()}
            </span>
          </div>

          <div className="flex items-center justify-between sm:justify-start gap-4 p-3 rounded-[--radius-lg] bg-surface-2/40 border border-border">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-destructive inline-block shadow-xs" />
              <span className="text-xs font-semibold text-muted-foreground">
                Pending Due
              </span>
            </div>
            <span className="text-xs font-bold text-error font-mono tabular-numbers">
              ₹{pending.toLocaleString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
