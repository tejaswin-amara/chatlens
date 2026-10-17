'use client';

import { useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  XCircle,
  Calculator,
  Bookmark,
  Trash2,
} from '@/components/ui/icons';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { triggerHaptic } from '@/lib/fluid-motion';

interface SimpleCalculatorProps {
  totalClasses: number;
  presents: number;
}

export function SimpleCalculator({
  totalClasses,
  presents,
}: SimpleCalculatorProps) {
  const calculatePercentage = () => {
    if (totalClasses === 0) return 0;
    return (presents / totalClasses) * 100;
  };

  const percentage = calculatePercentage();

  // Calculate how many classes can be missed while still maintaining 75%
  const calculateClassesCanMiss = (targetPercentage: number) => {
    if (percentage < targetPercentage) return 0;
    const numerator = 100 * presents - targetPercentage * totalClasses;
    const denominator = targetPercentage;
    if (denominator === 0) return 0;
    const classesCanMiss = Math.floor(numerator / denominator);
    return Math.max(0, classesCanMiss);
  };

  const classesCanMiss = calculateClassesCanMiss(75);

  // Calculate classes needed to reach 75% and 85%
  const calculateClassesNeeded = (targetPercentage: number) => {
    if (percentage >= targetPercentage) return 0;
    const numerator = targetPercentage * totalClasses - 100 * presents;
    const denominator = 100 - targetPercentage;
    if (denominator === 0) return 0;
    const classesNeeded = Math.ceil(numerator / denominator);
    return Math.max(0, classesNeeded);
  };

  const classesToAttend75 = calculateClassesNeeded(75);
  const classesToAttend85 = calculateClassesNeeded(85);

  // Determine the color based on attendance policy
  const getAttendanceColor = () => {
    if (percentage >= 85) return 'text-success';
    if (percentage >= 75) return 'text-warning';
    return 'text-destructive';
  };

  const getAttendanceStatus = () => {
    if (percentage >= 85) return 'Eligible';
    if (percentage >= 75) return 'Conditional Eligibility';
    return 'Not Eligible';
  };

  const attendanceColor = getAttendanceColor();
  const attendanceStatus = getAttendanceStatus();

  return (
    <div className="space-y-6">
      <div className="apple-card rounded-[--radius-2xl] p-6 shadow-xl border border-border relative overflow-hidden">
        <div className="flex flex-col space-y-2 mb-6">
          <h3 className="section-title text-foreground">Attendance Analysis</h3>
          <div className="flex items-baseline gap-3">
            <span
              className={`text-4xl font-bold tabular-numbers tracking-tight font-heading ${attendanceColor}`}
            >
              {percentage.toFixed(2)}%
            </span>
            <span
              className={`text-sm font-semibold tracking-tight ${attendanceColor}`}
            >
              ({attendanceStatus})
            </span>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-start gap-3.5 p-3 rounded-[--radius-lg] bg-surface-2 border border-border">
            <div className="w-2.5 h-2.5 rounded-full bg-primary mt-1.5 shrink-0 shadow-[0_0_8px_rgba(129,140,248,0.8)]" />
            <div className="min-w-0 flex-1">
              <h4 className="text-xs font-semibold text-foreground tracking-tight">
                Classes you can miss
              </h4>
              <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                {classesCanMiss > 0 ? (
                  <>
                    You can miss{' '}
                    <strong className="text-foreground font-semibold tabular-numbers">
                      {classesCanMiss}
                    </strong>{' '}
                    more classes and still maintain 75% attendance.
                    <br />
                    <span className="font-mono text-[11px] text-muted-foreground/80">
                      Current:{' '}
                      <span className="tabular-numbers text-foreground">
                        {presents}/{totalClasses}
                      </span>{' '}
                      ({percentage.toFixed(2)}%) → After:{' '}
                      <span className="tabular-numbers text-foreground">
                        {presents}/{totalClasses + classesCanMiss}
                      </span>{' '}
                      (
                      {(
                        (presents / (totalClasses + classesCanMiss)) *
                        100
                      ).toFixed(2)}
                      %)
                    </span>
                  </>
                ) : (
                  'You cannot miss any more classes while maintaining 75% attendance.'
                )}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5 p-3 rounded-[--radius-lg] bg-surface-2 border border-border">
            <div className="w-2.5 h-2.5 rounded-full bg-warning mt-1.5 shrink-0 shadow-[0_0_8px_rgba(251,191,36,0.8)]" />
            <div className="min-w-0 flex-1">
              <h4 className="text-xs font-semibold text-foreground tracking-tight">
                Classes needed for 75%
              </h4>
              <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                {classesToAttend75 > 0 ? (
                  <>
                    You need to attend{' '}
                    <strong className="text-foreground font-semibold tabular-numbers">
                      {classesToAttend75}
                    </strong>{' '}
                    more classes to reach 75% attendance.
                    <br />
                    <span className="font-mono text-[11px] text-muted-foreground/80">
                      Current:{' '}
                      <span className="tabular-numbers text-foreground">
                        {presents}/{totalClasses}
                      </span>{' '}
                      ({percentage.toFixed(2)}%) → After:{' '}
                      <span className="tabular-numbers text-foreground">
                        {presents + classesToAttend75}/
                        {totalClasses + classesToAttend75}
                      </span>{' '}
                      (
                      {(
                        ((presents + classesToAttend75) /
                          (totalClasses + classesToAttend75)) *
                        100
                      ).toFixed(2)}
                      %)
                    </span>
                  </>
                ) : (
                  'You have already reached 75% attendance.'
                )}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5 p-3 rounded-[--radius-lg] bg-surface-2 border border-border">
            <div className="w-2.5 h-2.5 rounded-full bg-success mt-1.5 shrink-0 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
            <div className="min-w-0 flex-1">
              <h4 className="text-xs font-semibold text-foreground tracking-tight">
                Classes needed for 85%
              </h4>
              <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                {classesToAttend85 > 0 ? (
                  <>
                    You need to attend{' '}
                    <strong className="text-foreground font-semibold tabular-numbers">
                      {classesToAttend85}
                    </strong>{' '}
                    more classes to reach 85% attendance.
                    <br />
                    <span className="font-mono text-[11px] text-muted-foreground/80">
                      Current:{' '}
                      <span className="tabular-numbers text-foreground">
                        {presents}/{totalClasses}
                      </span>{' '}
                      ({percentage.toFixed(2)}%) → After:{' '}
                      <span className="tabular-numbers text-foreground">
                        {presents + classesToAttend85}/
                        {totalClasses + classesToAttend85}
                      </span>{' '}
                      (
                      {(
                        ((presents + classesToAttend85) /
                          (totalClasses + classesToAttend85)) *
                        100
                      ).toFixed(2)}
                      %)
                    </span>
                  </>
                ) : (
                  'You have already reached 85% attendance.'
                )}
              </p>
            </div>
          </div>
        </div>
      </div>

      {percentage >= 85 ? (
        <div
          role="alert"
          className="relative w-full rounded-[--radius-xl] border border-success/35 bg-success/10 p-4 text-sm flex items-start gap-3 shadow-lg"
        >
          <CheckCircle2 className="h-5 w-5 text-success shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <h5 className="font-semibold text-foreground tracking-tight">
              Eligible
            </h5>
            <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
              Your attendance is above the minimum required 85%. You are
              eligible to appear for the examination.
            </p>
          </div>
        </div>
      ) : percentage >= 75 ? (
        <div
          role="alert"
          className="relative w-full rounded-[--radius-xl] border border-warning/35 bg-warning/10 p-4 text-sm flex items-start gap-3 shadow-lg"
        >
          <AlertCircle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <h5 className="font-semibold text-foreground tracking-tight">
              Conditional Eligibility
            </h5>
            <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
              Your attendance is between 75% and 85%. You need to pay a
              condonation fine to be eligible for the examination.
            </p>
          </div>
        </div>
      ) : (
        <div
          role="alert"
          className="relative w-full rounded-[--radius-xl] border border-destructive/35 bg-destructive/10 p-4 text-sm flex items-start gap-3 shadow-lg"
        >
          <XCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <h5 className="font-semibold text-foreground tracking-tight">
              Not Eligible
            </h5>
            <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
              Your attendance is below 75%. You may face detention and will not
              be eligible to appear for the examination.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export interface LTPSState {
  lecture: string;
  tutorial: string;
  practical: string;
  skilling: string;
  subjectName: string;
}

export interface LTPSCalculationResult {
  weightedPercentage: number;
  totalWeight: number;
  status: 'Eligible' | 'Conditional' | 'Not Eligible';
  color: string;
  activeComponents: { name: string; weight: number; value: number }[];
}

export function calculateLTPS(state: LTPSState): LTPSCalculationResult | null {
  const l = parseFloat(state.lecture);
  const t = parseFloat(state.tutorial);
  const p = parseFloat(state.practical);
  const s = parseFloat(state.skilling);

  let weightedSum = 0;
  let totalWeight = 0;
  const activeComponents: { name: string; weight: number; value: number }[] =
    [];

  if (!isNaN(l)) {
    weightedSum += l * 1.0;
    totalWeight += 1.0;
    activeComponents.push({ name: 'Lecture', weight: 100, value: l });
  }
  if (!isNaN(t)) {
    weightedSum += t * 0.25;
    totalWeight += 0.25;
    activeComponents.push({ name: 'Tutorial', weight: 25, value: t });
  }
  if (!isNaN(p)) {
    weightedSum += p * 0.5;
    totalWeight += 0.5;
    activeComponents.push({ name: 'Practical', weight: 50, value: p });
  }
  if (!isNaN(s)) {
    weightedSum += s * 0.25;
    totalWeight += 0.25;
    activeComponents.push({ name: 'Skilling', weight: 25, value: s });
  }

  if (totalWeight === 0) return null;

  const weightedPercentage =
    Math.round((weightedSum / totalWeight) * 100) / 100;

  let status: 'Eligible' | 'Conditional' | 'Not Eligible' = 'Not Eligible';
  let color = 'text-destructive';

  if (weightedPercentage >= 85) {
    status = 'Eligible';
    color = 'text-success';
  } else if (weightedPercentage >= 75) {
    status = 'Conditional';
    color = 'text-warning';
  }

  return {
    weightedPercentage,
    totalWeight,
    status,
    color,
    activeComponents,
  };
}

export function LTPSAttendanceCalculator() {
  const [lecture, setLecture] = useState('');
  const [tutorial, setTutorial] = useState('');
  const [practical, setPractical] = useState('');
  const [skilling, setSkilling] = useState('');
  const [subjectName, setSubjectName] = useState('');
  const [result, setResult] = useState<LTPSCalculationResult | null>(null);
  const [drafts, setDrafts] = useState<
    { id: string; name: string; state: LTPSState; pct: number }[]
  >(() => {
    if (typeof window === 'undefined') return [];
    try {
      const stored = localStorage.getItem('kl_ltps_drafts');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const handleCalculate = (e?: React.FormEvent) => {
    e?.preventDefault();
    triggerHaptic('light');
    const res = calculateLTPS({
      lecture,
      tutorial,
      practical,
      skilling,
      subjectName,
    });
    setResult(res);

    if (res && subjectName.trim()) {
      const newDraft = {
        id: Date.now().toString(),
        name: subjectName.trim(),
        state: {
          lecture,
          tutorial,
          practical,
          skilling,
          subjectName: subjectName.trim(),
        },
        pct: res.weightedPercentage,
      };
      const updated = [
        newDraft,
        ...drafts.filter((d) => d.name !== subjectName.trim()),
      ].slice(0, 5);
      setDrafts(updated);
      try {
        localStorage.setItem('kl_ltps_drafts', JSON.stringify(updated));
      } catch {}
    }
  };

  const loadDraft = (draft: { state: LTPSState }) => {
    triggerHaptic('selection');
    setLecture(draft.state.lecture);
    setTutorial(draft.state.tutorial);
    setPractical(draft.state.practical);
    setSkilling(draft.state.skilling);
    setSubjectName(draft.state.subjectName);
    setResult(calculateLTPS(draft.state));
  };

  const deleteDraft = (id: string) => {
    triggerHaptic('selection');
    const updated = drafts.filter((d) => d.id !== id);
    setDrafts(updated);
    try {
      localStorage.setItem('kl_ltps_drafts', JSON.stringify(updated));
    } catch {}
  };

  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground font-heading inline-block relative">
          LTPS Attendance Calculator
          <div className="absolute -bottom-2 left-0 right-0 h-1 bg-gradient-to-r from-red-500 via-rose-500 to-red-600 rounded-full" />
        </h2>
      </div>

      <div className="apple-card rounded-[--radius-2xl] p-6 sm:p-8 border border-border shadow-2xl space-y-6">
        <div>
          <h3 className="text-xl font-bold text-foreground font-heading">
            Calculate Attendance
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Enter your attendance percentages for each component
          </p>
        </div>

        <form onSubmit={handleCalculate} className="space-y-6">
          {/* 2x2 Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Lecture */}
            <div className="space-y-2">
              <label
                htmlFor="ltps-lecture"
                className="text-xs font-semibold text-foreground/90 block"
              >
                Lecture (100%)
              </label>
              <Input
                id="ltps-lecture"
                type="number"
                min="0"
                max="100"
                step="0.01"
                placeholder="Enter lecture attendance"
                value={lecture}
                onChange={(e) => setLecture(e.target.value)}
                className="tabular-numbers font-medium text-sm"
              />
            </div>

            {/* Tutorial */}
            <div className="space-y-2">
              <label
                htmlFor="ltps-tutorial"
                className="text-xs font-semibold text-foreground/90 block"
              >
                Tutorial (25%)
              </label>
              <Input
                id="ltps-tutorial"
                type="number"
                min="0"
                max="100"
                step="0.01"
                placeholder="Enter tutorial attendance"
                value={tutorial}
                onChange={(e) => setTutorial(e.target.value)}
                className="tabular-numbers font-medium text-sm"
              />
            </div>

            {/* Practical */}
            <div className="space-y-2">
              <label
                htmlFor="ltps-practical"
                className="text-xs font-semibold text-foreground/90 block"
              >
                Practical (50%)
              </label>
              <Input
                id="ltps-practical"
                type="number"
                min="0"
                max="100"
                step="0.01"
                placeholder="Enter practical attendance"
                value={practical}
                onChange={(e) => setPractical(e.target.value)}
                className="tabular-numbers font-medium text-sm"
              />
            </div>

            {/* Skilling */}
            <div className="space-y-2">
              <label
                htmlFor="ltps-skilling"
                className="text-xs font-semibold text-foreground/90 block"
              >
                Skilling (25%)
              </label>
              <Input
                id="ltps-skilling"
                type="number"
                min="0"
                max="100"
                step="0.01"
                placeholder="Enter skilling attendance"
                value={skilling}
                onChange={(e) => setSkilling(e.target.value)}
                className="tabular-numbers font-medium text-sm"
              />
            </div>
          </div>

          {/* Subject Name Draft Field */}
          <div className="space-y-2">
            <label
              htmlFor="ltps-subject"
              className="text-xs font-semibold text-foreground/90 flex items-center gap-2"
            >
              Subject Name{' '}
              <span className="text-muted-foreground font-normal">
                (Optional - to save as draft)
              </span>
            </label>
            <Input
              id="ltps-subject"
              type="text"
              placeholder="Enter subject name to save as draft"
              value={subjectName}
              onChange={(e) => setSubjectName(e.target.value)}
              className="text-sm"
            />
          </div>

          <Button
            type="submit"
            size="lg"
            className="w-full min-h-[48px] bg-primary hover:bg-primary/90 text-primary-foreground font-semibold text-sm shadow-lg shadow-primary/20 active:scale-[0.98] transition-all"
          >
            <Calculator className="w-4 h-4 mr-2" />
            Calculate
          </Button>
        </form>

        {/* Calculation Result */}
        {result && (
          <div className="pt-6 border-t border-border space-y-4 animate-spring-scale">
            <div className="flex items-baseline justify-between gap-4 p-4 rounded-[--radius-xl] bg-surface-2/60 border border-border">
              <div>
                <p className="caption-label text-muted-foreground">
                  Weighted LTPS Percentage
                </p>
                <div className="flex items-baseline gap-3 mt-1">
                  <span
                    className={`text-4xl font-extrabold tabular-numbers font-heading tracking-tight ${result.color}`}
                  >
                    {result.weightedPercentage.toFixed(2)}%
                  </span>
                  <span
                    className={`text-sm font-semibold tracking-tight ${result.color}`}
                  >
                    ({result.status})
                  </span>
                </div>
              </div>
            </div>

            {/* Policy Alert Banner */}
            {result.weightedPercentage >= 85 ? (
              <div
                role="alert"
                className="rounded-[--radius-xl] border border-success/35 bg-success/10 p-4 text-sm flex items-start gap-3 shadow-lg"
              >
                <CheckCircle2 className="h-5 w-5 text-success shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <h5 className="font-semibold text-foreground tracking-tight">
                    Eligible for Examinations
                  </h5>
                  <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                    Your weighted LTPS attendance is above 85%. You meet the
                    standard eligibility requirement with no condonation fee.
                  </p>
                </div>
              </div>
            ) : result.weightedPercentage >= 75 ? (
              <div
                role="alert"
                className="rounded-[--radius-xl] border border-warning/35 bg-warning/10 p-4 text-sm flex items-start gap-3 shadow-lg"
              >
                <AlertCircle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <h5 className="font-semibold text-foreground tracking-tight">
                    Condonation Range (75% – 85%)
                  </h5>
                  <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                    Your weighted attendance is in the condonation range. You
                    will be permitted to sit for examinations upon paying the
                    university condonation fine.
                  </p>
                </div>
              </div>
            ) : (
              <div
                role="alert"
                className="rounded-[--radius-xl] border border-destructive/35 bg-destructive/10 p-4 text-sm flex items-start gap-3 shadow-lg"
              >
                <XCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <h5 className="font-semibold text-foreground tracking-tight">
                    Detention Risk (&lt; 75%)
                  </h5>
                  <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                    Your weighted attendance is below the mandatory 75% cutoff.
                    You are at high risk of academic detention unless immediate
                    attendance is recovered.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Saved Drafts */}
        {drafts.length > 0 && (
          <div className="pt-4 border-t border-border space-y-2">
            <p className="caption-label text-muted-foreground flex items-center gap-1.5">
              <Bookmark className="w-3.5 h-3.5 text-primary" />
              Saved Subject Drafts
            </p>
            <div className="flex flex-wrap gap-2">
              {drafts.map((d) => (
                <div
                  key={d.id}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-[--radius-lg] bg-surface-2 border border-border text-xs hover:border-primary/25 transition-all"
                >
                  <button
                    type="button"
                    onClick={() => loadDraft(d)}
                    className="font-medium text-foreground hover:text-primary transition-colors flex items-center gap-1.5 min-h-[44px]"
                  >
                    <span>{d.name}</span>
                    <span className="text-muted-foreground font-mono tabular-numbers font-normal">
                      ({d.pct}%)
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteDraft(d.id)}
                    className="text-muted-foreground hover:text-destructive transition-colors min-h-[44px] min-w-[44px] p-2"
                    aria-label={`Delete ${d.name}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
