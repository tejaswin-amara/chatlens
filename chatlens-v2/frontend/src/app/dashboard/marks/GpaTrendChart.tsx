'use client';

import * as React from 'react';

export interface GpaTrendChartProps {
  data: Record<string, unknown>[];
}

export function GpaTrendChart({ data }: GpaTrendChartProps) {
  if (!data || data.length === 0) return null;

  // Extract marks / grades from dataset
  const points = data
    .map((row, idx) => {
      let label = '';
      let score = 0;

      for (const [key, val] of Object.entries(row)) {
        const k = key.toLowerCase();
        if (
          k.includes('code') ||
          k.includes('subject') ||
          k.includes('title')
        ) {
          if (!label) label = String(val);
        }
        if (
          k.includes('grade') ||
          k.includes('marks') ||
          k.includes('cgpa') ||
          k.includes('total') ||
          k.includes('score')
        ) {
          const num = parseFloat(String(val));
          if (!isNaN(num)) score = num;
        }
      }

      if (!label) label = `Course ${idx + 1}`;
      return {
        label: label.length > 10 ? label.substring(0, 8) + '…' : label,
        fullLabel: label,
        score,
      };
    })
    .filter((p) => p.score >= 0);

  if (points.length === 0) return null;

  const maxScore = Math.max(10, ...points.map((p) => p.score));
  const chartHeight = 220;
  const paddingLeft = 40;
  const paddingBottom = 40;
  const paddingTop = 25;
  const paddingRight = 25;
  const svgWidth = 600;
  const innerWidth = svgWidth - paddingLeft - paddingRight;
  const innerHeight = chartHeight - paddingTop - paddingBottom;

  const step =
    points.length > 1 ? innerWidth / (points.length - 1) : innerWidth;

  const svgPoints = points.map((p, i) => {
    const x = paddingLeft + (points.length > 1 ? i * step : innerWidth / 2);
    const y = paddingTop + innerHeight - (p.score / maxScore) * innerHeight;
    return { ...p, x, y };
  });

  const pathD = svgPoints.reduce((acc, p, i) => {
    return i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
  }, '');

  const areaD =
    svgPoints.length > 0
      ? `${pathD} L ${svgPoints[svgPoints.length - 1].x} ${paddingTop + innerHeight} L ${svgPoints[0].x} ${paddingTop + innerHeight} Z`
      : '';

  return (
    <div className="rounded-[--radius-2xl] border border-border apple-card p-6 space-y-4 shadow-xl overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground font-heading tracking-tight">
            Performance Trend
          </h3>
          <p className="text-xs text-muted-foreground/80 font-normal">
            Subject performance scores
          </p>
        </div>
        <div className="text-xs font-mono font-bold text-primary bg-primary/10 border border-primary/20 px-2.5 py-1 rounded-full apple-pill">
          Max: {maxScore}
        </div>
      </div>

      <div className="w-full overflow-x-auto custom-scrollbar">
        <svg
          viewBox={`0 0 ${svgWidth} ${chartHeight}`}
          className="w-full h-auto min-w-[500px]"
          role="img"
          aria-label="GPA Performance Trend Chart"
        >
          <defs>
            <linearGradient id="gpaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Y Gridlines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const val = Math.round(ratio * maxScore);
            const y = paddingTop + innerHeight - ratio * innerHeight;
            return (
              <g key={ratio}>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={svgWidth - paddingRight}
                  y2={y}
                  stroke="rgba(255, 255, 255, 0.08)"
                />
                <text
                  x={paddingLeft - 8}
                  y={y + 4}
                  textAnchor="end"
                  className="fill-muted-foreground text-[10px] font-mono"
                >
                  {val}
                </text>
              </g>
            );
          })}

          {/* Area fill */}
          <path d={areaD} fill="url(#gpaGradient)" />

          {/* Trend Line */}
          <path
            d={pathD}
            fill="none"
            stroke="#818cf8"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Points */}
          {svgPoints.map((p, idx) => (
            <g key={idx} className="group">
              <title>{`${p.fullLabel}: ${p.score}`}</title>
              <circle
                cx={p.x}
                cy={p.y}
                r="5"
                fill="#6366f1"
                stroke="#ffffff"
                strokeWidth="2"
                className="transition-transform group-hover:scale-125"
              />
              <text
                x={p.x}
                y={p.y - 10}
                textAnchor="middle"
                className="fill-foreground text-[10px] font-bold font-mono"
              >
                {p.score}
              </text>
              <text
                x={p.x}
                y={chartHeight - 12}
                textAnchor="middle"
                className="fill-muted-foreground text-[9px] font-medium"
              >
                {p.label}
              </text>
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}
