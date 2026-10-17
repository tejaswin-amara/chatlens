'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Loader2,
  Wrench,
  AlertCircle,
  Percent,
  Target,
  Calculator,
} from '@/components/ui/icons';
import {
  SimpleCalculator,
  LTPSAttendanceCalculator,
} from '@/components/attendance-calculator';
import { processERPDataForCGPA } from '@/lib/cgpa';
import { triggerHaptic } from '@/lib/fluid-motion';

export default function ToolsPage() {
  const [activeTab, setActiveTab] = useState<'target' | 'ltps' | 'cgpa'>(
    'target'
  );
  const [totalClasses, setTotalClasses] = useState(0);
  const [presents, setPresents] = useState(0);
  const [cgpa, setCgpa] = useState<number>(0);
  const [completedCredits, setCompletedCredits] = useState<number>(0);
  const [loading, setLoading] = useState(false);

  const [targetCgpa, setTargetCgpa] = useState<string>('9.0');
  const [newCredits, setNewCredits] = useState<string>('24');

  const fetchData = useCallback(async () => {
    try {
      const cgpaRes = await fetch('/api/erp-proxy/cgpa');
      const cgpaData = await cgpaRes.json();
      if (cgpaData.success && cgpaData.data && cgpaData.data.length > 0) {
        const result = processERPDataForCGPA(cgpaData.data);
        setCompletedCredits(result.credits);
        setCgpa(result.cgpa);
      }

      const yearStr =
        localStorage.getItem('kl_erp_academic_years') ||
        sessionStorage.getItem('kl_erp_academic_years');
      const semStr =
        localStorage.getItem('kl_erp_semesters') ||
        sessionStorage.getItem('kl_erp_semesters');
      let yearId = localStorage.getItem('kl_erp_year') || '';
      let semId = localStorage.getItem('kl_erp_sem') || '';
      if (!yearId && yearStr) {
        try {
          const parsed = JSON.parse(yearStr);
          if (Array.isArray(parsed) && parsed.length > 0)
            yearId = parsed[0]?.value || '';
        } catch {}
      }
      if (!semId && semStr) {
        try {
          const parsed = JSON.parse(semStr);
          if (Array.isArray(parsed) && parsed.length > 0)
            semId = parsed[0]?.value || '';
        } catch {}
      }
      if (!yearId) yearId = '2025-2026';
      if (!semId) semId = '1';

      if (yearId && semId) {
        const attRes = await fetch('/api/erp-proxy/attendance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ academicYear: yearId, semesterId: semId }),
        });
        const attData = await attRes.json();
        if (attData.success && attData.attendanceData) {
          let totalConducted = 0;
          let totalAttended = 0;
          attData.attendanceData.forEach((row: Record<string, unknown>) => {
            const condKey = Object.keys(row).find(
              (k) =>
                k.toLowerCase().includes('conducted') ||
                k.toLowerCase().includes('held') ||
                (k.toLowerCase().includes('total') &&
                  !k.toLowerCase().includes('%'))
            );
            const attKey = Object.keys(row).find(
              (k) =>
                k.toLowerCase().includes('attended') ||
                k.toLowerCase().includes('present')
            );
            if (condKey && attKey) {
              totalConducted += parseFloat(String(row[condKey])) || 0;
              totalAttended += parseFloat(String(row[attKey])) || 0;
            }
          });
          setTotalClasses(totalConducted);
          setPresents(totalAttended);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      const cachedCgpa = localStorage.getItem('kl_dashboard_cgpa');
      const cachedCredits = localStorage.getItem('kl_dashboard_credits');
      if (cachedCgpa) setCgpa(Number(cachedCgpa));
      if (cachedCredits) setCompletedCredits(Number(cachedCredits));
      fetchData();
    });
  }, [fetchData]);

  const calculateRequiredGpa = () => {
    const target = parseFloat(targetCgpa);
    const futureCreds = parseFloat(newCredits);
    if (isNaN(target) || isNaN(futureCreds) || futureCreds <= 0) return null;

    const currentPoints = cgpa * completedCredits;
    const requiredPoints =
      target * (completedCredits + futureCreds) - currentPoints;
    const requiredGpa = requiredPoints / futureCreds;
    return requiredGpa.toFixed(2);
  };

  const reqGpa = calculateRequiredGpa();

  return (
    <div className="flex flex-col gap-6 w-full animate-spring-up">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-3xl font-semibold tracking-[-0.025em] text-foreground font-heading flex items-center gap-3">
            <Wrench className="w-8 h-8 text-primary" />
            Tools & Calculators
          </h2>
          <p className="text-xs text-muted-foreground/90 mt-1 font-normal">
            Smart academic tools pre-populated with your live ERP attendance and
            marks data.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-surface-2/60 border border-border rounded-[--radius-lg] p-1 gap-1">
          <button
            type="button"
            onClick={() => {
              triggerHaptic('selection');
              setActiveTab('target');
            }}
            className={`px-3 py-1.5 rounded-[--radius-md] text-xs font-semibold flex items-center gap-1.5 transition-all min-h-[44px] ${
              activeTab === 'target'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Percent className="w-3.5 h-3.5" />
            <span>Target Calculator</span>
          </button>

          <button
            type="button"
            onClick={() => {
              triggerHaptic('selection');
              setActiveTab('ltps');
            }}
            className={`px-3 py-1.5 rounded-[--radius-md] text-xs font-semibold flex items-center gap-1.5 transition-all min-h-[44px] ${
              activeTab === 'ltps'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Calculator className="w-3.5 h-3.5" />
            <span>LTPS Calculator</span>
          </button>

          <button
            type="button"
            onClick={() => {
              triggerHaptic('selection');
              setActiveTab('cgpa');
            }}
            className={`px-3 py-1.5 rounded-[--radius-md] text-xs font-semibold flex items-center gap-1.5 transition-all min-h-[44px] ${
              activeTab === 'cgpa'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Target className="w-3.5 h-3.5" />
            <span>CGPA Predictor</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center h-64 border border-border rounded-[--radius-2xl] apple-card shadow-xl">
          <Loader2 className="w-8 h-8 text-primary animate-spin mb-4" />
          <p className="text-xs text-muted-foreground font-medium">
            Loading your data...
          </p>
        </div>
      ) : activeTab === 'ltps' ? (
        <div className="max-w-2xl mx-auto w-full">
          <LTPSAttendanceCalculator />
        </div>
      ) : activeTab === 'cgpa' ? (
        <div className="max-w-2xl mx-auto w-full">
          {/* CGPA Goal Predictor */}
          <div className="rounded-[--radius-2xl] border border-border apple-card p-6 sm:p-8 shadow-2xl relative overflow-hidden flex flex-col">
            <div className="p-4 border-b border-border flex items-center gap-3 bg-surface-2/30 rounded-t-[--radius-xl] -mx-6 sm:-mx-8 -mt-6 sm:-mt-8 mb-6">
              <Target className="w-5 h-5 text-primary" />
              <h3 className="text-base font-semibold text-foreground font-heading tracking-tight">
                CGPA Goal Predictor
              </h3>
            </div>
            <div className="flex-1 flex flex-col gap-6">
              <div className="flex items-center gap-6 p-4 bg-primary/10 border border-primary/25 rounded-[--radius-xl]">
                <div className="flex-1 text-center">
                  <p className="caption-label text-primary mb-1">
                    Current CGPA
                  </p>
                  <p className="text-3xl font-extrabold text-foreground tabular-numbers font-heading">
                    {cgpa.toFixed(2)}
                  </p>
                </div>
                <div className="w-px h-10 bg-primary/25" />
                <div className="flex-1 text-center">
                  <p className="caption-label text-primary mb-1">
                    Earned Credits
                  </p>
                  <p className="text-3xl font-extrabold text-foreground tabular-numbers font-heading">
                    {completedCredits}
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <div className="flex-1">
                  <label
                    htmlFor="target-cgpa-input"
                    className="caption-label text-muted-foreground/90 block mb-2"
                  >
                    Target CGPA Goal
                  </label>
                  <input
                    id="target-cgpa-input"
                    type="number"
                    step="0.1"
                    className="w-full bg-surface-2/60 border border-border rounded-[--radius-lg] px-4 py-2.5 text-foreground text-sm font-semibold tabular-numbers focus:outline-hidden focus:border-primary/50 transition-all"
                    value={targetCgpa}
                    onChange={(e) => {
                      triggerHaptic('selection');
                      setTargetCgpa(e.target.value);
                    }}
                  />
                </div>
                <div className="flex-1">
                  <label
                    htmlFor="upcoming-credits-input"
                    className="caption-label text-muted-foreground/90 block mb-2"
                  >
                    Upcoming Credits
                  </label>
                  <input
                    id="upcoming-credits-input"
                    type="number"
                    className="w-full bg-surface-2/60 border border-border rounded-[--radius-lg] px-4 py-2.5 text-foreground text-sm font-semibold tabular-numbers focus:outline-hidden focus:border-primary/50 transition-all"
                    value={newCredits}
                    onChange={(e) => {
                      triggerHaptic('selection');
                      setNewCredits(e.target.value);
                    }}
                  />
                </div>
              </div>

              <div className="mt-auto p-5 bg-surface-2/40 border border-border rounded-[--radius-xl] text-center">
                {reqGpa === null ? (
                  <p className="text-muted-foreground text-xs font-normal">
                    Enter valid numbers.
                  </p>
                ) : parseFloat(reqGpa) > 10 ? (
                  <div>
                    <p className="text-destructive font-semibold mb-1 flex items-center justify-center gap-2 text-sm tracking-tight">
                      <AlertCircle className="w-4 h-4" /> Unreachable Goal
                    </p>
                    <p className="text-muted-foreground text-xs leading-relaxed font-normal">
                      You would need an upcoming GPA of{' '}
                      <strong className="text-destructive tabular-numbers font-semibold">
                        {reqGpa}
                      </strong>
                      .
                    </p>
                  </div>
                ) : parseFloat(reqGpa) < 0 ? (
                  <div>
                    <p className="text-success font-semibold mb-1 flex items-center justify-center gap-2 text-sm tracking-tight">
                      <Target className="w-4 h-4" /> Easily Achievable
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-muted-foreground text-xs mb-1 font-normal">
                      Required upcoming GPA to hit {targetCgpa}
                    </p>
                    <p className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-primary to-info tabular-numbers font-heading tracking-tight">
                      {reqGpa}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Attendance Target Card */}
          <div className="rounded-[--radius-2xl] border border-border apple-card p-6 shadow-2xl relative overflow-hidden flex flex-col h-full">
            <div className="p-4 border-b border-border flex items-center gap-3 bg-surface-2/30 rounded-t-[--radius-xl] -mx-6 -mt-6 mb-6">
              <Percent className="w-5 h-5 text-success" />
              <h3 className="text-base font-semibold text-foreground font-heading tracking-tight">
                Attendance Target
              </h3>
            </div>
            <div className="flex-1 flex flex-col gap-6">
              <p className="text-xs text-muted-foreground font-normal leading-relaxed">
                Your total classes conducted and attended have been synced
                automatically from the ERP.
              </p>

              <div className="flex gap-4">
                <div className="flex-1">
                  <label
                    htmlFor="total-classes-input"
                    className="caption-label text-muted-foreground/90 block mb-2"
                  >
                    Total Classes
                  </label>
                  <input
                    id="total-classes-input"
                    type="number"
                    className="w-full bg-surface-2/60 border border-border rounded-[--radius-lg] px-4 py-2.5 text-foreground text-sm font-semibold tabular-numbers focus:outline-hidden focus:border-success/50 transition-all"
                    value={totalClasses}
                    onChange={(e) => {
                      triggerHaptic('selection');
                      setTotalClasses(parseInt(e.target.value) || 0);
                    }}
                  />
                </div>
                <div className="flex-1">
                  <label
                    htmlFor="classes-attended-input"
                    className="caption-label text-muted-foreground/90 block mb-2"
                  >
                    Classes Attended
                  </label>
                  <input
                    id="classes-attended-input"
                    type="number"
                    className="w-full bg-surface-2/60 border border-border rounded-[--radius-lg] px-4 py-2.5 text-foreground text-sm font-semibold tabular-numbers focus:outline-hidden focus:border-success/50 transition-all"
                    value={presents}
                    onChange={(e) => {
                      triggerHaptic('selection');
                      setPresents(parseInt(e.target.value) || 0);
                    }}
                  />
                </div>
              </div>

              <div className="overflow-hidden mt-4">
                <SimpleCalculator
                  totalClasses={totalClasses}
                  presents={presents}
                />
              </div>
            </div>
          </div>

          {/* CGPA Goal Predictor Preview */}
          <div className="rounded-[--radius-2xl] border border-border apple-card p-6 shadow-2xl relative overflow-hidden flex flex-col h-full">
            <div className="p-4 border-b border-border flex items-center gap-3 bg-surface-2/30 rounded-t-[--radius-xl] -mx-6 -mt-6 mb-6">
              <Target className="w-5 h-5 text-primary" />
              <h3 className="text-base font-semibold text-foreground font-heading tracking-tight">
                CGPA Goal Predictor
              </h3>
            </div>
            <div className="flex-1 flex flex-col gap-6">
              <div className="flex items-center gap-6 p-4 bg-primary/10 border border-primary/25 rounded-[--radius-xl]">
                <div className="flex-1 text-center">
                  <p className="caption-label text-primary mb-1">
                    Current CGPA
                  </p>
                  <p className="text-3xl font-extrabold text-foreground tabular-numbers font-heading">
                    {cgpa.toFixed(2)}
                  </p>
                </div>
                <div className="w-px h-10 bg-primary/25" />
                <div className="flex-1 text-center">
                  <p className="caption-label text-primary mb-1">
                    Earned Credits
                  </p>
                  <p className="text-3xl font-extrabold text-foreground tabular-numbers font-heading">
                    {completedCredits}
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <div className="flex-1">
                  <label
                    htmlFor="target-cgpa-input-2"
                    className="caption-label text-muted-foreground/90 block mb-2"
                  >
                    Target CGPA Goal
                  </label>
                  <input
                    id="target-cgpa-input-2"
                    type="number"
                    step="0.1"
                    className="w-full bg-surface-2/60 border border-border rounded-[--radius-lg] px-4 py-2.5 text-foreground text-sm font-semibold tabular-numbers focus:outline-hidden focus:border-primary/50 transition-all"
                    value={targetCgpa}
                    onChange={(e) => {
                      triggerHaptic('selection');
                      setTargetCgpa(e.target.value);
                    }}
                  />
                </div>
                <div className="flex-1">
                  <label
                    htmlFor="upcoming-credits-input-2"
                    className="caption-label text-muted-foreground/90 block mb-2"
                  >
                    Upcoming Credits
                  </label>
                  <input
                    id="upcoming-credits-input-2"
                    type="number"
                    className="w-full bg-surface-2/60 border border-border rounded-[--radius-lg] px-4 py-2.5 text-foreground text-sm font-semibold tabular-numbers focus:outline-hidden focus:border-primary/50 transition-all"
                    value={newCredits}
                    onChange={(e) => {
                      triggerHaptic('selection');
                      setNewCredits(e.target.value);
                    }}
                  />
                </div>
              </div>

              <div className="mt-auto p-5 bg-surface-2/40 border border-border rounded-[--radius-xl] text-center">
                {reqGpa === null ? (
                  <p className="text-muted-foreground text-xs font-normal">
                    Enter valid numbers.
                  </p>
                ) : parseFloat(reqGpa) > 10 ? (
                  <div>
                    <p className="text-destructive font-semibold mb-1 flex items-center justify-center gap-2 text-sm tracking-tight">
                      <AlertCircle className="w-4 h-4" /> Unreachable Goal
                    </p>
                    <p className="text-muted-foreground text-xs leading-relaxed font-normal">
                      You would need an upcoming GPA of{' '}
                      <strong className="text-destructive tabular-numbers font-semibold">
                        {reqGpa}
                      </strong>
                      .
                    </p>
                  </div>
                ) : parseFloat(reqGpa) < 0 ? (
                  <div>
                    <p className="text-success font-semibold mb-1 flex items-center justify-center gap-2 text-sm tracking-tight">
                      <Target className="w-4 h-4" /> Easily Achievable
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-muted-foreground text-xs mb-1 font-normal">
                      Required upcoming GPA to hit {targetCgpa}
                    </p>
                    <p className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-primary to-info tabular-numbers font-heading tracking-tight">
                      {reqGpa}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
