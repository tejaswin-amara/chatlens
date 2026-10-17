'use client';

import { useState, useMemo } from 'react';
import { useAcademicSession } from '@/hooks/useAcademicSession';
import { useAttendance } from '@/hooks/useAttendance';
import { PageHeader } from '@/components/ui/page-header';
import { Select } from '@/components/ui/select';
import { EmptyState } from '@/components/ui/empty-state';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { AttendanceChart } from './AttendanceChart';
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  LayoutGrid,
  List,
} from '@/components/ui/icons';
import { getSubjectTitle, getSubjectCode } from '@/lib/course-utils';
import { triggerHaptic } from '@/lib/fluid-motion';

export interface AttendanceComponent {
  name: string;
  weight: number; // 1.0, 0.5, 0.25
  weightPercentage: number; // 100, 50, 25
  attended: number;
  conducted: number;
  percentage: number;
}

export interface GroupedSubjectAttendance {
  subjectCode: string;
  subjectTitle: string;
  overallPercentage: number;
  totalAttended: number;
  totalConducted: number;
  components: AttendanceComponent[];
  rawRows: Record<string, unknown>[];
}

interface ProjectionItem {
  componentName: string;
  type: 'skip' | 'need';
  count: number | string;
  targetOverall: number;
  projectedAttended: number;
  projectedConducted: number;
  label: string;
}

function normalizeBaseCode(rawCode: string): string {
  if (!rawCode) return '';
  return rawCode
    .trim()
    .toUpperCase()
    .replace(/[-_](L|P|S|T|LEC|PRAC|LAB|SKILL|TUT)$/i, '')
    .replace(/\s*\((L|P|S|T|LEC|PRAC|LAB|SKILL|TUT)\)$/i, '')
    .replace(/\s*\[(L|P|S|T|LEC|PRAC|LAB|SKILL|TUT)\]$/i, '');
}

function normalizeBaseTitle(rawTitle: string): string {
  if (!rawTitle) return '';
  return rawTitle
    .trim()
    .toUpperCase()
    .replace(
      /\s*[-–—]\s*(LECTURE|PRACTICAL|SKILLING|TUTORIAL|LAB|SKILL|TUT|LEC|PRAC)$/i,
      ''
    )
    .replace(
      /\s*\((LECTURE|PRACTICAL|SKILLING|TUTORIAL|LAB|SKILL|TUT|L|P|S|T)\)$/i,
      ''
    )
    .replace(
      /\s*\[(LECTURE|PRACTICAL|SKILLING|TUTORIAL|LAB|SKILL|TUT|L|P|S|T)\]$/i,
      ''
    )
    .trim();
}

function extractEmbeddedComponentsFromRow(
  row: Record<string, unknown>
): AttendanceComponent[] {
  const components: AttendanceComponent[] = [];
  const entries = Object.entries(row);

  const defs = [
    {
      name: 'Lecture',
      weight: 1.0,
      weightPercentage: 100,
      patterns: ['lecture', 'lec', '_l', ' l '],
    },
    {
      name: 'Practical',
      weight: 0.5,
      weightPercentage: 50,
      patterns: ['practical', 'prac', 'lab', '_p', ' p '],
    },
    {
      name: 'Skilling',
      weight: 0.25,
      weightPercentage: 25,
      patterns: ['skilling', 'skill', '_s', ' s '],
    },
    {
      name: 'Tutorial',
      weight: 0.25,
      weightPercentage: 25,
      patterns: ['tutorial', 'tut', '_t', ' t '],
    },
  ];

  defs.forEach(({ name, weight, weightPercentage, patterns }) => {
    let cond = 0;
    let att = 0;
    let found = false;

    patterns.forEach((pat) => {
      const matchCond = entries.find(([k]) => {
        const kl = k.toLowerCase();
        return (
          kl.includes(pat) &&
          (kl.includes('conduct') ||
            kl.includes('total') ||
            kl.includes('held'))
        );
      });
      const matchAtt = entries.find(([k]) => {
        const kl = k.toLowerCase();
        return (
          kl.includes(pat) && (kl.includes('attend') || kl.includes('present'))
        );
      });

      if (matchCond && matchAtt) {
        const c = parseFloat(String(matchCond[1]));
        const a = parseFloat(String(matchAtt[1]));
        if (!isNaN(c) && !isNaN(a) && c > 0) {
          cond = c;
          att = a;
          found = true;
        }
      }
    });

    if (found) {
      const pct = cond > 0 ? Math.round((att / cond) * 10000) / 100 : 100;
      components.push({
        name,
        weight,
        weightPercentage,
        attended: att,
        conducted: cond,
        percentage: pct,
      });
    }
  });

  return components;
}

function detectComponentMeta(
  row: Record<string, unknown>,
  rawCode: string,
  rawTitle: string
): { name: string; weight: number; weightPercentage: number } {
  let detected = '';
  const entries = Object.entries(row);

  for (const [k, v] of entries) {
    const key = k.toLowerCase();
    if (
      key.includes('component') ||
      key.includes('course type') ||
      key.includes('session type') ||
      key.includes('subject type') ||
      key.includes('type') ||
      key.includes('category')
    ) {
      const val = String(v).trim().toLowerCase();
      if (val.includes('skil') || val === 's') detected = 'Skilling';
      else if (val.includes('prac') || val.includes('lab') || val === 'p')
        detected = 'Practical';
      else if (val.includes('tut') || val === 't') detected = 'Tutorial';
      else if (val.includes('lec') || val === 'l') detected = 'Lecture';
    }
  }

  if (!detected && rawCode) {
    const code = rawCode.trim().toUpperCase();
    if (
      code.endsWith('-S') ||
      code.endsWith('(S)') ||
      code.endsWith(' SKILLING')
    )
      detected = 'Skilling';
    else if (
      code.endsWith('-P') ||
      code.endsWith('(P)') ||
      code.endsWith(' PRACTICAL') ||
      code.endsWith(' LAB')
    )
      detected = 'Practical';
    else if (
      code.endsWith('-T') ||
      code.endsWith('(T)') ||
      code.endsWith(' TUTORIAL')
    )
      detected = 'Tutorial';
    else if (
      code.endsWith('-L') ||
      code.endsWith('(L)') ||
      code.endsWith(' LECTURE')
    )
      detected = 'Lecture';
  }

  if (!detected && rawTitle) {
    const title = rawTitle.toLowerCase();
    if (title.includes('skilling') || title.includes('skill'))
      detected = 'Skilling';
    else if (title.includes('practical') || title.includes('lab'))
      detected = 'Practical';
    else if (title.includes('tutorial') || title.includes('tut'))
      detected = 'Tutorial';
    else if (title.includes('lecture') || title.includes('lec'))
      detected = 'Lecture';
  }

  detected = detected || 'Lecture';

  switch (detected) {
    case 'Skilling':
      return { name: 'Skilling', weight: 0.25, weightPercentage: 25 };
    case 'Practical':
      return { name: 'Practical', weight: 0.5, weightPercentage: 50 };
    case 'Tutorial':
      return { name: 'Tutorial', weight: 0.25, weightPercentage: 25 };
    case 'Lecture':
    default:
      return { name: 'Lecture', weight: 1.0, weightPercentage: 100 };
  }
}

/**
 * Ensures all course components (Lecture, Practical, Skilling) are present together
 * matching the university's full LTPS curriculum structure.
 */
function expandToFullLTPSComponents(
  totalConducted: number,
  totalAttended: number,
  overallPct: number,
  existingComponents: AttendanceComponent[]
): AttendanceComponent[] {
  // Return real components only — never fabricate synthetic breakdowns
  if (existingComponents.length > 0) {
    return existingComponents;
  }

  // Fallback: create a single aggregate component from totals
  const pct = totalConducted > 0 ? Math.round((totalAttended / totalConducted) * 10000) / 100 : (overallPct || 100);
  return [{
    name: 'Aggregate',
    weight: 1.0,
    weightPercentage: 100,
    attended: totalAttended,
    conducted: totalConducted,
    percentage: pct,
  }];
}

export function groupAttendanceRows(
  rawRows: Record<string, unknown>[]
): GroupedSubjectAttendance[] {
  if (!rawRows || rawRows.length === 0) return [];

  const subjectMap = new Map<
    string,
    {
      baseCode: string;
      baseTitle: string;
      componentsMap: Map<string, AttendanceComponent>;
      rawRows: Record<string, unknown>[];
      fallbackTotalAttended: number;
      fallbackTotalConducted: number;
      fallbackPct: number;
    }
  >();

  rawRows.forEach((row) => {
    let rawCode = '';
    let rawTitle = '';
    let conducted = 0;
    let attended = 0;
    let percentage = 0;

    Object.entries(row).forEach(([k, v]) => {
      const key = k.toLowerCase();
      if (key.includes('code') || key.includes('subject code'))
        rawCode = String(v).trim();
      if (
        key.includes('title') ||
        key.includes('subject title') ||
        key.includes('name') ||
        key.includes('course name')
      ) {
        rawTitle = String(v).trim();
      }
      if (
        key.includes('conducted') ||
        (key.includes('total') && !key.includes('%'))
      ) {
        const num = parseFloat(String(v));
        if (!isNaN(num)) conducted = num;
      }
      if (
        key.includes('attended') ||
        (key.includes('present') && !key.includes('%'))
      ) {
        const num = parseFloat(String(v));
        if (!isNaN(num)) attended = num;
      }
      if (typeof v === 'string' && v.includes('%')) {
        const num = parseFloat(v);
        if (!isNaN(num)) percentage = num;
      }
    });

    if (!rawCode && !rawTitle && Object.keys(row).length > 0) {
      rawCode = String(Object.values(row)[0]);
    }

    const baseCode = normalizeBaseCode(rawCode) || getSubjectCode(rawCode);
    const baseTitle =
      normalizeBaseTitle(rawTitle) || getSubjectTitle(rawCode, rawTitle);
    const groupKey = baseCode ? baseCode : baseTitle;

    if (!subjectMap.has(groupKey)) {
      subjectMap.set(groupKey, {
        baseCode,
        baseTitle,
        componentsMap: new Map(),
        rawRows: [],
        fallbackTotalAttended: 0,
        fallbackTotalConducted: 0,
        fallbackPct: 0,
      });
    }

    const subjectEntry = subjectMap.get(groupKey)!;
    subjectEntry.rawRows.push(row);
    subjectEntry.fallbackTotalAttended += attended;
    subjectEntry.fallbackTotalConducted += conducted;
    if (percentage > 0) subjectEntry.fallbackPct = percentage;

    // Check if row has embedded multi-component columns (Lecture, Practical, etc.)
    const embeddedComps = extractEmbeddedComponentsFromRow(row);
    if (embeddedComps.length > 0) {
      embeddedComps.forEach((comp) => {
        subjectEntry.componentsMap.set(comp.name, comp);
      });
    } else {
      const compMeta = detectComponentMeta(row, rawCode, rawTitle);
      const compPct =
        conducted > 0
          ? Math.round((attended / conducted) * 10000) / 100
          : percentage || 100;

      if (subjectEntry.componentsMap.has(compMeta.name)) {
        const existing = subjectEntry.componentsMap.get(compMeta.name)!;
        const totalAtt = existing.attended + attended;
        const totalCond = existing.conducted + conducted;
        subjectEntry.componentsMap.set(compMeta.name, {
          ...existing,
          attended: totalAtt,
          conducted: totalCond,
          percentage:
            totalCond > 0
              ? Math.round((totalAtt / totalCond) * 10000) / 100
              : 100,
        });
      } else {
        subjectEntry.componentsMap.set(compMeta.name, {
          name: compMeta.name,
          weight: compMeta.weight,
          weightPercentage: compMeta.weightPercentage,
          attended,
          conducted,
          percentage: compPct,
        });
      }
    }
  });

  return Array.from(subjectMap.values()).map(
    ({
      baseCode,
      baseTitle,
      componentsMap,
      rawRows,
      fallbackTotalAttended,
      fallbackTotalConducted,
      fallbackPct,
    }) => {
      const rawComponents = Array.from(componentsMap.values());

      // Ensure all course components are present together
      const components = expandToFullLTPSComponents(
        fallbackTotalConducted,
        fallbackTotalAttended,
        fallbackPct,
        rawComponents
      );

      // Sort: Lecture (100%), Practical (50%), Skilling (25%), Tutorial (25%)
      const sortOrder: Record<string, number> = {
        Lecture: 1,
        Practical: 2,
        Skilling: 3,
        Tutorial: 4,
      };
      components.sort(
        (a, b) => (sortOrder[a.name] || 99) - (sortOrder[b.name] || 99)
      );

      let totalWeight = 0;
      let weightedSum = 0;
      let totalAttended = 0;
      let totalConducted = 0;

      components.forEach((c) => {
        weightedSum += c.percentage * c.weight;
        totalWeight += c.weight;
        totalAttended += c.attended;
        totalConducted += c.conducted;
      });

      const overallPercentage =
        totalWeight > 0
          ? Math.round((weightedSum / totalWeight) * 100) / 100
          : fallbackPct || 100;

      return {
        subjectCode: baseCode,
        subjectTitle: baseTitle || getSubjectTitle(baseCode, ''),
        overallPercentage,
        totalAttended,
        totalConducted,
        components,
        rawRows,
      };
    }
  );
}

function calculateSubjectProjections(subject: GroupedSubjectAttendance): {
  statusHeader: string;
  isSafe: boolean;
  projections: ProjectionItem[];
} {
  const { components, overallPercentage } = subject;
  const totalWeight = components.reduce((sum, c) => sum + c.weight, 0);
  const projections: ProjectionItem[] = [];

  if (totalWeight === 0 || components.length === 0) {
    return { statusHeader: 'ON TRACK', isSafe: true, projections: [] };
  }

  let totalSkipsPossible = 0;

  components.forEach((comp) => {
    const otherWeightedSum = components
      .filter((c) => c !== comp)
      .reduce((sum, c) => sum + c.percentage * c.weight, 0);

    // Calculate Skips for 75%
    const target75 = 75;
    const required75 = target75 * totalWeight - otherWeightedSum;

    if (required75 <= 0) {
      projections.push({
        componentName: comp.name,
        type: 'skip',
        count: '>50',
        targetOverall: 75,
        projectedAttended: comp.attended,
        projectedConducted: comp.conducted + 50,
        label: `>50 ${comp.name} (maintain 75% overall)`,
      });
      totalSkipsPossible += 50;
    } else {
      const maxConducted = (100 * comp.attended * comp.weight) / required75;
      const skips75 = Math.floor(maxConducted - comp.conducted);
      if (skips75 > 0) {
        totalSkipsPossible += skips75;
        projections.push({
          componentName: comp.name,
          type: 'skip',
          count: skips75 > 50 ? '>50' : skips75,
          targetOverall: 75,
          projectedAttended: comp.attended,
          projectedConducted: comp.conducted + (skips75 > 50 ? 50 : skips75),
          label: `${skips75 > 50 ? '>50' : skips75} ${comp.name} (maintain 75% overall)`,
        });
      }
    }

    // Calculate Skips / Needed for 85%
    const target85 = 85;
    const required85 = target85 * totalWeight - otherWeightedSum;

    if (required85 <= 0) {
      projections.push({
        componentName: comp.name,
        type: 'skip',
        count: '>50',
        targetOverall: 85,
        projectedAttended: comp.attended,
        projectedConducted: comp.conducted + 50,
        label: `>50 ${comp.name} (maintain 85% overall)`,
      });
    } else {
      const maxConducted85 = (100 * comp.attended * comp.weight) / required85;
      const skips85 = Math.floor(maxConducted85 - comp.conducted);
      if (skips85 > 0 && skips85 <= 50) {
        projections.push({
          componentName: comp.name,
          type: 'skip',
          count: skips85,
          targetOverall: 85,
          projectedAttended: comp.attended,
          projectedConducted: comp.conducted + skips85,
          label: `${skips85} ${comp.name} (maintain 85% overall)`,
        });
      } else if (skips85 < 0) {
        const targetFraction = required85 / (100 * comp.weight);
        if (targetFraction < 1) {
          const needed = Math.ceil(
            (targetFraction * comp.conducted - comp.attended) /
              (1 - targetFraction)
          );
          if (needed > 0) {
            projections.push({
              componentName: comp.name,
              type: 'need',
              count: needed,
              targetOverall: 85,
              projectedAttended: comp.attended + needed,
              projectedConducted: comp.conducted + needed,
              label: `${needed} ${comp.name} (reach 85% overall)`,
            });
          }
        }
      }
    }
  });

  const isSafe = overallPercentage >= 75;
  const statusHeader =
    totalSkipsPossible > 0
      ? `SAFE TO SKIP (Any ${totalSkipsPossible})`
      : overallPercentage >= 85
        ? 'ATTENDANCE STABLE'
        : 'ATTENDANCE REQUIRED';

  return {
    statusHeader,
    isSafe,
    projections,
  };
}

function UnifiedSubjectCard({
  subject,
}: {
  subject: GroupedSubjectAttendance;
}) {
  const pct = subject.overallPercentage;
  const isEligible = pct >= 85;
  const isConditional = pct >= 75 && pct < 85;

  const accentBorder = isEligible
    ? 'border-l-success'
    : isConditional
      ? 'border-l-warning'
      : 'border-l-error';

  const statusColor = isEligible
    ? 'text-success'
    : isConditional
      ? 'text-warning'
      : 'text-error';

  const statusLabel = isEligible
    ? 'Eligible'
    : isConditional
      ? 'Conditional'
      : 'Not Eligible';

  const { statusHeader, isSafe, projections } = useMemo(
    () => calculateSubjectProjections(subject),
    [subject]
  );

  return (
    <div
      className={`rounded-[--radius-2xl] apple-card overflow-hidden p-5 sm:p-7 border border-border ${accentBorder} border-l-[6px] shadow-xl space-y-6 transition-all duration-[--duration-normal] hover:border-primary/30`}
    >
      {/* Top Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="text-base sm:text-lg font-bold text-foreground uppercase tracking-tight line-clamp-2 leading-snug">
            {subject.subjectTitle}
          </h3>
          {subject.subjectCode && (
            <p className="text-xs font-mono text-muted-foreground/90 mt-1 tracking-wider uppercase font-semibold">
              {subject.subjectCode}
            </p>
          )}
        </div>
        <div className="text-right shrink-0">
          <div
            className={`text-3xl sm:text-4xl font-extrabold tabular-numbers font-heading tracking-tight ${statusColor}`}
          >
            {Math.round(pct)}%
          </div>
          <div
            className={`text-xs font-semibold tracking-tight mt-0.5 ${statusColor}`}
          >
            {statusLabel}
          </div>
        </div>
      </div>

      {/* Two-Column Body: Components & Projections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-5 border-t border-border">
        {/* Left Column: Components */}
        <div className="space-y-3.5">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Components
          </h4>
          <div className="space-y-3">
            {subject.components.map((comp, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between text-xs py-0.5"
              >
                <span className="text-muted-foreground font-medium">
                  <strong className="text-foreground font-semibold">
                    {comp.name}
                  </strong>{' '}
                  <span className="text-[11px] text-muted-foreground/80 font-normal">
                    (Weightage: {comp.weightPercentage}%)
                  </span>
                </span>
                <span className="text-foreground font-semibold tabular-numbers text-right text-xs">
                  {comp.attended}/{comp.conducted}{' '}
                  <span className="text-muted-foreground/90 font-normal">
                    ({Math.round(comp.percentage)}%)
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Projections */}
        <div className="space-y-3.5 md:border-l md:border-border md:pl-8">
          <div>
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
              Projections
            </h4>
            <span
              className={`text-[11px] font-bold tracking-wide uppercase ${
                isSafe ? 'text-success' : 'text-error'
              }`}
            >
              {statusHeader}
            </span>
          </div>

          <div className="space-y-2.5 pt-1 border-t border-border">
            {projections.length > 0 ? (
              projections.map((proj, idx) => {
                const color =
                  proj.type === 'skip'
                    ? proj.targetOverall === 75
                      ? 'text-success'
                      : 'text-success'
                    : 'text-error';

                return (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-xs py-0.5"
                  >
                    <span className="text-muted-foreground">
                      <strong className={`font-semibold ${color}`}>
                        {proj.count} {proj.componentName}
                      </strong>{' '}
                      <span className="text-[11px]">
                        ({proj.type === 'skip' ? 'maintain' : 'reach'}{' '}
                        {proj.targetOverall}% overall)
                      </span>
                    </span>
                    <span className="text-muted-foreground/80 font-mono text-[11px] tabular-numbers">
                      ({proj.projectedAttended}/{proj.projectedConducted})
                    </span>
                  </div>
                );
              })
            ) : (
              <div className="text-xs text-muted-foreground/80 italic py-1">
                Attendance requirement currently balanced.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AttendanceDashboard() {
  const {
    years,
    semesters,
    selectedYear,
    selectedSem,
    handleYearChange,
    handleSemChange,
  } = useAcademicSession();
  const {
    raw: dataRaw,
    overallPercentage: overallPct,
    totalAttended: overallAttended,
    totalConducted: overallConducted,
    isLoading: loading,
    error: fetchError,
    mutate,
  } = useAttendance(selectedYear, selectedSem);

  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');

  const error = fetchError ? fetchError.message : null;
  const data = useMemo(() => dataRaw || [], [dataRaw]);

  // Group multiple rows/components into unified subjects with full component breakdown
  const unifiedSubjects = useMemo(() => groupAttendanceRows(data), [data]);

  return (
    <div className="flex flex-col gap-6 w-full animate-spring-up">
      <PageHeader
        title="Attendance"
        description="Real-time attendance synced from ERP"
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center bg-surface-2/60 border border-border rounded-[--radius-lg] p-1 gap-1">
              <button
                type="button"
                onClick={() => {
                  triggerHaptic('selection');
                  setViewMode('cards');
                }}
                className={`px-3 py-1.5 rounded-[--radius-md] text-xs font-semibold flex items-center gap-1.5 transition-all min-h-[44px] ${
                  viewMode === 'cards'
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-surface-3'
                }`}
                aria-label="Cards view"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                <span>Cards</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  triggerHaptic('selection');
                  setViewMode('table');
                }}
                className={`px-3 py-1.5 rounded-[--radius-md] text-xs font-semibold flex items-center gap-1.5 transition-all min-h-[44px] ${
                  viewMode === 'table'
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-surface-3'
                }`}
                aria-label="Table view"
              >
                <List className="w-3.5 h-3.5" />
                <span>Table</span>
              </button>
            </div>

            <Select
              options={years}
              value={selectedYear}
              onChange={(e) => handleYearChange(e.target.value)}
              aria-label="Select Academic Year"
            />
            <Select
              options={semesters}
              value={selectedSem}
              onChange={(e) => handleSemChange(e.target.value)}
              aria-label="Select Semester"
            />
          </div>
        }
      />

      {/* Overall Stats */}
      {!loading && !error && data.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-[--radius-2xl] apple-card p-5 flex items-center gap-4 shadow-xl border border-border">
            <Progress
              value={overallPct}
              max={100}
              variant="circular"
              size="lg"
              showLabel
              colorByValue
            />
            <div>
              <p className="caption-label text-muted-foreground/80">Overall</p>
              <p className="text-2xl font-bold text-foreground tabular-numbers tracking-tight font-heading">
                {overallPct}%
              </p>
            </div>
          </div>
          <div className="rounded-[--radius-2xl] apple-card p-5 shadow-xl border border-border">
            <p className="caption-label text-muted-foreground/80 mb-1">
              Classes Attended
            </p>
            <p className="text-3xl font-bold text-foreground tabular-numbers tracking-tight font-heading">
              {overallAttended}
            </p>
          </div>
          <div className="rounded-[--radius-2xl] apple-card p-5 shadow-xl border border-border">
            <p className="caption-label text-muted-foreground/80 mb-1">
              Classes Held
            </p>
            <p className="text-3xl font-bold text-foreground tabular-numbers tracking-tight font-heading">
              {overallConducted}
            </p>
          </div>
        </div>
      )}

      {/* Attendance Chart */}
      {!loading && !error && data.length > 0 && <AttendanceChart data={data} />}

      {/* Attendance Cards / Table */}
      <div>
        {loading ? (
          <div className="p-6 space-y-4 rounded-[--radius-2xl] apple-card border border-border shadow-xl">
            {[...Array(4)].map((_, i) => (
              <Skeleton
                key={i}
                className="h-44 w-full rounded-[--radius-2xl]"
              />
            ))}
          </div>
        ) : error ? (
          <div className="rounded-[--radius-2xl] apple-card overflow-hidden shadow-xl border border-border p-4">
            <EmptyState
              variant="error"
              description={error}
              action={{ label: 'Retry', onClick: () => mutate() }}
            />
          </div>
        ) : data.length === 0 ? (
          <div className="rounded-[--radius-2xl] apple-card overflow-hidden shadow-xl border border-border p-4">
            <EmptyState
              title="No attendance records"
              description="Records will appear once available in the ERP."
            />
          </div>
        ) : viewMode === 'cards' ? (
          <div className="space-y-5">
            {unifiedSubjects.map((subject, idx) => (
              <UnifiedSubjectCard
                key={subject.subjectCode || idx}
                subject={subject}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-[--radius-2xl] apple-card overflow-hidden shadow-xl border border-border">
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface-2/40 sticky top-0 z-10 backdrop-blur-md">
                    {Object.keys(data[0] || {}).map((key, i) => (
                      <th
                        key={i}
                        scope="col"
                        className="px-5 py-3.5 caption-label text-muted-foreground whitespace-nowrap text-left"
                      >
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.map((row, idx) => (
                    <tr
                      key={idx}
                      className="hover:bg-surface-2 transition-colors"
                    >
                      {Object.values(row).map((val: unknown, j: number) => {
                        let displayVal: React.ReactNode = String(val);

                        if (typeof val === 'string' && val.includes('%')) {
                          const num = parseFloat(val);
                          if (!isNaN(num)) {
                            const Icon =
                              num >= 85
                                ? TrendingUp
                                : num >= 75
                                  ? AlertTriangle
                                  : TrendingDown;
                            const colorClass =
                              num >= 85
                                ? 'bg-success/15 text-success border border-success/25'
                                : num >= 75
                                  ? 'bg-warning/15 text-warning border border-warning/25'
                                  : 'bg-destructive/15 text-destructive border border-destructive/25';

                            displayVal = (
                              <span
                                className={`inline-flex items-center gap-1 ${colorClass} px-2.5 py-0.5 rounded-full text-xs font-bold tabular-numbers apple-pill`}
                              >
                                <Icon className="w-3 h-3" />
                                {val}
                              </span>
                            );
                          }
                        }

                        return (
                          <td
                            key={j}
                            className="px-5 py-3.5 text-sm text-foreground tabular-numbers font-medium"
                          >
                            {displayVal}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
