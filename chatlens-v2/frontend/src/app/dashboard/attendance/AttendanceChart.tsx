'use client';

import * as React from 'react';
import { getSubjectTitle, getSubjectCode } from '@/lib/course-utils';

export interface AttendanceChartProps {
  data: Record<string, unknown>[];
}

export function AttendanceChart({ data }: AttendanceChartProps) {
  if (!data || data.length === 0) return null;

  // Group by base code/title so each subject has one consolidated chart bar
  const subjectMap = new Map<
    string,
    {
      subjectName: string;
      shortName: string;
      subjectCode: string;
      weightedPctSum: number;
      weightSum: number;
    }
  >();

  data.forEach((row) => {
    let rawCode = '';
    let rawTitle = '';
    let pct = 0;
    let weight = 1.0;

    for (const [key, val] of Object.entries(row)) {
      const k = key.toLowerCase();
      const strVal = String(val ?? '').trim();

      if (k.includes('code') || k.includes('coursecode')) {
        if (!rawCode) rawCode = strVal;
      } else if (
        k.includes('title') ||
        k.includes('subject') ||
        k.includes('coursename') ||
        k.includes('coursedesc')
      ) {
        if (!rawTitle) rawTitle = strVal;
      } else if (
        !rawCode &&
        !rawTitle &&
        /^[0-9]{2}[A-Z]{2,5}[0-9]{3,4}[A-Z]?$/i.test(strVal)
      ) {
        rawCode = strVal;
      }

      if (typeof val === 'string' && val.includes('%')) {
        const num = parseFloat(val);
        if (!isNaN(num)) pct = num;
      } else if (
        k.includes('percentage') ||
        k.includes('pct') ||
        k.includes('att %')
      ) {
        const num = parseFloat(String(val));
        if (!isNaN(num)) pct = num;
      }

      if (k.includes('component') || k.includes('type')) {
        const t = strVal.toLowerCase();
        if (t.includes('skil') || t === 's') weight = 0.25;
        else if (t.includes('prac') || t.includes('lab') || t === 'p')
          weight = 0.5;
        else if (t.includes('tut') || t === 't') weight = 0.25;
        else if (t.includes('lec') || t === 'l') weight = 1.0;
      }
    }

    if (!rawCode && !rawTitle) {
      rawTitle = String(Object.values(row)[0] || 'Subject');
    }

    const baseCode = getSubjectCode(rawCode, rawTitle);
    const subjectName = getSubjectTitle(rawCode, rawTitle);
    const groupKey = baseCode || subjectName;

    if (!subjectMap.has(groupKey)) {
      let shortName = subjectName;
      if (shortName.length > 11) {
        shortName = shortName.substring(0, 10).trim() + '…';
      }
      subjectMap.set(groupKey, {
        subjectName,
        shortName,
        subjectCode: baseCode,
        weightedPctSum: pct * weight,
        weightSum: weight,
      });
    } else {
      const existing = subjectMap.get(groupKey)!;
      existing.weightedPctSum += pct * weight;
      existing.weightSum += weight;
    }
  });

  const items = Array.from(subjectMap.values())
    .map((item) => ({
      subjectName: item.subjectName,
      shortName: item.shortName,
      subjectCode: item.subjectCode,
      pct:
        item.weightSum > 0
          ? Math.round((item.weightedPctSum / item.weightSum) * 100) / 100
          : 100,
    }))
    .filter((item) => item.pct >= 0);

  if (items.length === 0) return null;

  const chartHeight = 260;
  const paddingLeft = 45;
  const paddingBottom = 65;
  const paddingTop = 25;
  const paddingRight = 25;

  // Dynamically expand SVG width according to item count to ensure zero text collision
  const minItemWidth = 65;
  const svgWidth = Math.max(
    680,
    paddingLeft + paddingRight + items.length * minItemWidth
  );
  const innerWidth = svgWidth - paddingLeft - paddingRight;
  const innerHeight = chartHeight - paddingTop - paddingBottom;

  const step = innerWidth / items.length;
  const barWidth = Math.min(36, Math.max(18, step * 0.55));

  return (
    <div className="rounded-[--radius-2xl] border border-border apple-card p-6 space-y-4 shadow-xl overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground font-heading tracking-tight">
            Subject Attendance Breakdown
          </h3>
          <p className="text-xs text-muted-foreground/80 font-normal">
            Percentage overview per subject
          </p>
        </div>
        <div className="flex items-center gap-3 text-[11px] font-semibold">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-success inline-block shadow-xs" />{' '}
            ≥85%
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-warning inline-block shadow-xs" />{' '}
            75-84%
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-destructive inline-block shadow-xs" />{' '}
            &lt;75%
          </span>
        </div>
      </div>

      <div className="w-full overflow-x-auto custom-scrollbar">
        <svg
          viewBox={`0 0 ${svgWidth} ${chartHeight}`}
          className="w-full h-auto min-w-[650px]"
          role="img"
          aria-label="Attendance Bar Chart"
        >
          {/* Grid lines (0%, 25%, 50%, 75%, 100%) */}
          {[0, 25, 50, 75, 100].map((val) => {
            const y = paddingTop + innerHeight - (val / 100) * innerHeight;
            return (
              <g key={val}>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={svgWidth - paddingRight}
                  y2={y}
                  stroke={
                    val === 75
                      ? 'rgba(245, 158, 11, 0.4)'
                      : 'rgba(255, 255, 255, 0.10)'
                  }
                  strokeDasharray={val === 75 ? '4 4' : undefined}
                />
                <text
                  x={paddingLeft - 8}
                  y={y + 4}
                  textAnchor="end"
                  className="fill-muted-foreground text-[10px] font-mono"
                >
                  {val}%
                </text>
              </g>
            );
          })}

          {/* Bars */}
          {items.map((item, idx) => {
            const x = paddingLeft + idx * step + (step - barWidth) / 2;
            const barH = (item.pct / 100) * innerHeight;
            const y = paddingTop + innerHeight - barH;

            const color =
              item.pct >= 85
                ? 'var(--color-success, #10b981)'
                : item.pct >= 75
                  ? 'var(--color-warning, #f59e0b)'
                  : 'var(--color-error, #ef4444)';

            const labelX = x + barWidth / 2;

            return (
              <g key={idx} className="group">
                <title>{`${item.subjectName} (${item.subjectCode || 'No Code'}): ${item.pct}%`}</title>
                {/* Bar */}
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barH}
                  rx={6}
                  fill={color}
                  opacity={0.88}
                  className="transition-all duration-[--duration-normal] group-hover:opacity-100 cursor-pointer"
                />
                {/* Value text above bar */}
                <text
                  x={labelX}
                  y={y - 6}
                  textAnchor="middle"
                  className="fill-foreground text-[10px] font-bold font-mono tabular-numbers"
                >
                  {Math.round(item.pct)}%
                </text>

                {/* Subject Name as Title under bar */}
                <text
                  x={labelX}
                  y={chartHeight - 32}
                  textAnchor="middle"
                  className="fill-foreground text-[10px] font-semibold tracking-tight"
                >
                  {item.shortName}
                </text>

                {/* Subject Code under Subject Name */}
                {item.subjectCode && (
                  <text
                    x={labelX}
                    y={chartHeight - 16}
                    textAnchor="middle"
                    className="fill-muted-foreground text-[9px] font-mono font-medium"
                  >
                    {item.subjectCode}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
