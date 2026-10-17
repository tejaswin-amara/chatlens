'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  GraduationCap,
  CalendarDays,
  TrendingUp,
  BookOpen,
  Calendar as CalendarIcon,
  Wallet,
  Activity,
  Award,
  ChevronRight,
  MapPin,
  User,
  RefreshCw,
  AlertCircle,
  Clock,
} from '@/components/ui/icons';

import { StatCard } from '@/components/ui/stat-card';
import { EmptyState } from '@/components/ui/empty-state';
import { Badge } from '@/components/ui/badge';
import { triggerHaptic } from '@/lib/fluid-motion';
import { getCachedValue } from '@/hooks/useNativeQuery';

import { calculatePendingFee } from '@/lib/fee-utils';
import { processERPDataForCGPA } from '@/lib/cgpa';
import { getSubjectTitle, getSubjectCode } from '@/lib/course-utils';
import {
  parseTimetable,
  isSameDay,
  NormalizedClassSession,
} from '@/lib/timetable-parser';

export default function DashboardOverview() {
  const [studentName, setStudentName] = useState('Student');
  const [cgpa, setCgpa] = useState<number>(0);
  const [attendance, setAttendance] = useState<number>(0);
  const [pendingFee, setPendingFee] = useState<number>(0);
  const [completedCredits, setCompletedCredits] = useState<number>(0);
  const [activeYearId, setActiveYearId] = useState<string>('');
  const [activeSemId, setActiveSemId] = useState<string>('');
  const [syncError, setSyncError] = useState<string | null>(null);
  const [rateLimitSeconds, setRateLimitSeconds] = useState<number | null>(null);

  useEffect(() => {
    if (rateLimitSeconds === null || rateLimitSeconds <= 0) return;
    const timer = setInterval(() => {
      setRateLimitSeconds((prev) => (prev && prev > 1 ? prev - 1 : null));
    }, 1000);
    return () => clearInterval(timer);
  }, [rateLimitSeconds]);

  useEffect(() => {
    queueMicrotask(() => {
      const name = localStorage.getItem('kl_student_name');
      if (name) setStudentName(name);

      // Instant cache hydration
      const cachedCgpa = localStorage.getItem('kl_dashboard_cgpa');
      const cachedCredits = localStorage.getItem('kl_dashboard_credits');
      const cachedAttendance = localStorage.getItem('kl_dashboard_attendance');
      const cachedFee = localStorage.getItem('kl_dashboard_fee');
      if (cachedCgpa) setCgpa(Number(cachedCgpa));
      if (cachedCredits) setCompletedCredits(Number(cachedCredits));
      if (cachedAttendance) setAttendance(Number(cachedAttendance));
      if (cachedFee) setPendingFee(Number(cachedFee));
    });

    // Background fetches
    fetch('/api/erp-proxy/cgpa')
      .then((res) => {
        if (res.status === 429) setRateLimitSeconds(60);
        return res.json();
      })
      .then((resData) => {
        if (resData.isRateLimit) setRateLimitSeconds(60);
        if (resData.success && resData.data && resData.data.length > 0) {
          const result = processERPDataForCGPA(resData.data);
          setCompletedCredits(result.credits);
          if (result.credits > 0)
            localStorage.setItem(
              'kl_dashboard_credits',
              result.credits.toString()
            );
          if (result.cgpa > 0) {
            setCgpa(result.cgpa);
            localStorage.setItem('kl_dashboard_cgpa', result.cgpa.toString());
          }
        } else if (!resData.success && resData.error && !resData.isRateLimit) {
          setSyncError(
            'ERP gateway temporarily slow or unavailable. Metrics may reflect cached data.'
          );
        }
      })
      .catch(() => {
        setSyncError(
          'ERP gateway temporarily slow or unreachable. Showing cached academic metrics.'
        );
      });

    queueMicrotask(() => {
      let yearId = localStorage.getItem('kl_erp_year') || '';
      let semId = localStorage.getItem('kl_erp_sem') || '';
      const yStr =
        localStorage.getItem('kl_erp_academic_years') ||
        sessionStorage.getItem('kl_erp_academic_years');
      const sStr =
        localStorage.getItem('kl_erp_semesters') ||
        sessionStorage.getItem('kl_erp_semesters');
      if (!yearId && yStr) {
        try {
          const years = JSON.parse(yStr);
          if (years.length > 0) yearId = years[0].value;
        } catch {}
      }
      if (!semId && sStr) {
        try {
          const semesters = JSON.parse(sStr);
          if (semesters.length > 0) semId = semesters[0].value;
        } catch {}
      }
      if (!yearId) yearId = '2025-2026';
      if (!semId) semId = '1';

      setActiveYearId(yearId);
      setActiveSemId(semId);

      if (yearId && semId) {
        fetch('/api/erp-proxy/attendance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ academicYear: yearId, semesterId: semId }),
        })
          .then((res) => {
            if (res.status === 429) setRateLimitSeconds(60);
            return res.json();
          })
          .then((resData) => {
            if (resData.isRateLimit) setRateLimitSeconds(60);
            if (
              resData.success &&
              resData.attendanceData &&
              resData.attendanceData.length > 0
            ) {
              let totalAttended = 0;
              let totalConducted = 0;
              const filteredAttendance = resData.attendanceData;

              filteredAttendance.forEach((row: Record<string, unknown>) => {
                const condKey = Object.keys(row).find((k) => {
                  const kl = k.toLowerCase();
                  return (
                    kl.includes('conducted') ||
                    kl.includes('held') ||
                    (kl.includes('total') && !kl.includes('%'))
                  );
                });
                const attKey = Object.keys(row).find((k) => {
                  const kl = k.toLowerCase();
                  return kl.includes('attended') || kl.includes('present');
                });
                if (condKey && attKey) {
                  totalConducted += parseFloat(String(row[condKey])) || 0;
                  totalAttended += parseFloat(String(row[attKey])) || 0;
                }
              });
              if (totalConducted > 0) {
                const calc = Math.round((totalAttended / totalConducted) * 100);
                setAttendance(calc);
                localStorage.setItem(
                  'kl_dashboard_attendance',
                  calc.toString()
                );
              }
            }
          })
          .catch(() => {
            setSyncError(
              'ERP gateway temporarily slow or unreachable. Showing cached academic metrics.'
            );
          });
      }
    });

    fetch('/api/erp-proxy/fee')
      .then((res) => {
        if (res.status === 429) setRateLimitSeconds(60);
        return res.json();
      })
      .then((resData) => {
        if (resData.isRateLimit) setRateLimitSeconds(60);
        if (resData.success && resData.data && resData.data.length > 0) {
          const pending = calculatePendingFee(resData.data);
          setPendingFee(pending);
          localStorage.setItem('kl_dashboard_fee', pending.toString());
        }
      })
      .catch(() => {
        setSyncError(
          'ERP gateway temporarily slow or unreachable. Showing cached academic metrics.'
        );
      });
  }, []);

  return (
    <div className="flex flex-col gap-6 w-full animate-spring-up">
      {rateLimitSeconds !== null && rateLimitSeconds > 0 && (
        <div className="flex items-center justify-between gap-3 p-3.5 rounded-[--radius-lg] bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-medium animate-in fade-in">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 shrink-0 text-amber-400 animate-spin" />
            <span>
              Official college ERP rate limit cooldown active. KL-Sync is
              protecting your university account by serving offline cached data.
              Resuming live sync in {rateLimitSeconds}s.
            </span>
          </div>
          <button
            onClick={() => setRateLimitSeconds(null)}
            className="px-3 py-1.5 rounded-md bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs font-semibold cursor-pointer transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          >
            Dismiss
          </button>
        </div>
      )}
      {syncError && !rateLimitSeconds && (
        <div className="flex items-center justify-between gap-3 p-3.5 rounded-[--radius-lg] bg-warning/10 border border-warning/25 text-warning text-xs font-medium">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-warning" />
            <span>{syncError}</span>
          </div>
          <button
            onClick={() => setSyncError(null)}
            className="px-3 py-1.5 rounded-md bg-warning/20 hover:bg-warning/30 text-warning text-xs font-semibold cursor-pointer transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          >
            Dismiss
          </button>
        </div>
      )}
      {/* Welcome Banner with Apple Specular Glass */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 rounded-[--radius-2xl] apple-card p-6 sm:p-8 relative overflow-hidden group shadow-xl">
          <div className="absolute top-0 right-0 p-6 opacity-[0.05] pointer-events-none transition-transform duration-700 group-hover:scale-105">
            <GraduationCap className="w-44 h-44 text-primary" />
          </div>
          <div className="relative z-10">
            <Badge
              variant="success"
              dot
              className="mb-4 text-[11px] tracking-wider uppercase apple-pill"
            >
              Live Sync Active
            </Badge>
            <h2 className="text-3xl sm:text-4xl font-normal text-foreground tracking-[-0.025em] font-heading">
              Welcome back,
              <br />
              <span
                className="text-gradient-brand font-bold"
                suppressHydrationWarning
              >
                {studentName}
              </span>
            </h2>
            <p className="text-muted-foreground mt-3 max-w-lg text-sm leading-relaxed font-normal">
              Your academic data is synced with the live ERP system.
            </p>
          </div>
        </div>

        {/* CGPA Card */}
        <div className="rounded-[--radius-2xl] apple-card p-6 flex flex-col items-center justify-center text-center relative overflow-hidden group hover:border-primary/30 transition-all duration-[--duration-normal] shadow-xl">
          <Award className="w-10 h-10 text-primary mb-3 opacity-70" />
          <p className="caption-label text-muted-foreground/80 mb-1">
            Cumulative GPA
          </p>
          <span
            className="text-5xl font-extrabold tracking-tight text-foreground tabular-numbers font-heading"
            suppressHydrationWarning
          >
            {cgpa > 0 ? cgpa.toFixed(2) : '0.00'}
          </span>
        </div>
      </section>

      {/* Quick Stats */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link
          href="/dashboard/attendance"
          onClick={() => triggerHaptic('selection')}
          className="group"
        >
          <StatCard
            label="Attendance"
            value={`${attendance > 0 ? attendance.toFixed(0) : '0'}%`}
            icon={Activity}
            accent="success"
          />
        </Link>
        <Link
          href="/dashboard/fee"
          onClick={() => triggerHaptic('selection')}
          className="group"
        >
          <StatCard
            label="Pending Fees"
            value={`₹${pendingFee > 0 ? pendingFee.toLocaleString() : '0'}`}
            icon={Wallet}
            accent="danger"
          />
        </Link>
        <Link
          href="/dashboard/marks"
          onClick={() => triggerHaptic('selection')}
          className="group"
        >
          <StatCard
            label="Completed Credits"
            value={completedCredits > 0 ? String(completedCredits) : '0'}
            icon={TrendingUp}
            accent="purple"
          />
        </Link>
      </section>

      {/* Main Content Grid */}
      <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <TodayScheduleWidget
          activeYearId={activeYearId}
          activeSemId={activeSemId}
        />
        <CurrentCoursesWidget
          activeYearId={activeYearId}
          activeSemId={activeSemId}
        />
      </section>
    </div>
  );
}

/* ── Today's Schedule Widget ── */
function TodayScheduleWidget({
  activeYearId,
  activeSemId,
}: {
  activeYearId: string;
  activeSemId: string;
}) {
  const days = [
    'Sunday',
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
  ];
  const todayDayName = days[new Date().getDay()];
  const availableDays = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ];

  const [allSessions, setAllSessions] = useState<NormalizedClassSession[]>([]);
  const [selectedDay, setSelectedDay] = useState<string>(todayDayName);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSchedule = useCallback(async () => {
    if (!activeYearId || !activeSemId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);

    const cacheKey = `kl_timetable_${activeYearId}_${activeSemId}`;
    let loadedFromCache = false;

    // Try cache first
    try {
      const cached = sessionStorage.getItem(cacheKey);
      if (cached) {
        const rawData = JSON.parse(cached);
        if (Array.isArray(rawData) && rawData.length > 0) {
          const parsed = parseTimetable(rawData);
          setAllSessions(parsed.sessions);
          loadedFromCache = true;
          setLoading(false);
        }
      }
    } catch {}

    // Fetch fresh
    try {
      const res = await fetch('/api/erp-proxy/timetable', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          academicYear: activeYearId,
          semesterId: activeSemId,
        }),
      });
      const resData = await res.json();
      if (resData.success && Array.isArray(resData.data)) {
        sessionStorage.setItem(cacheKey, JSON.stringify(resData.data));
        const parsed = parseTimetable(resData.data);
        setAllSessions(parsed.sessions);
        setError(null);
      } else if (!loadedFromCache) {
        setError(resData.error || 'Failed to sync timetable');
      }
    } catch (err: unknown) {
      if (!loadedFromCache) {
        setError(
          err instanceof Error
            ? err.message
            : 'Error connecting to timetable service'
        );
      }
    } finally {
      setLoading(false);
    }
  }, [activeYearId, activeSemId]);

  useEffect(() => {
    let cancelled = false;
    async function initSchedule() {
      await Promise.resolve();
      if (!cancelled) {
        loadSchedule();
      }
    }
    initSchedule();
    return () => {
      cancelled = true;
    };
  }, [loadSchedule]);

  const activeDaySessions = allSessions.filter((s) =>
    isSameDay(s.day, selectedDay)
  );

  return (
    <div className="rounded-[--radius-2xl] apple-card flex flex-col h-full overflow-hidden shadow-xl border border-border">
      {/* Header */}
      <div className="p-4 sm:p-5 border-b border-border flex flex-col gap-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2.5">
            <CalendarDays className="w-5 h-5 text-primary" />
            <div>
              <h3 className="text-sm font-semibold text-foreground tracking-tight font-heading">
                Daily Schedule
              </h3>
              <p className="text-[11px] text-muted-foreground font-mono tabular-numbers">
                Today is {todayDayName} • Viewing {selectedDay}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {error && (
              <button
                onClick={() => {
                  triggerHaptic('light');
                  loadSchedule();
                }}
                aria-label="Refresh timetable schedule"
                className="p-2 rounded-full hover:bg-surface-3 text-muted-foreground hover:text-foreground transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center cursor-pointer touch-manipulation active:scale-90"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            )}
            <Badge variant="success" dot className="text-[10px] apple-pill">
              Live
            </Badge>
          </div>
        </div>

        {/* Day Selector Segment Control with Spring Haptic Feedback */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 custom-scrollbar">
          {availableDays.map((d) => {
            const isSelected = isSameDay(d, selectedDay);
            const isToday = isSameDay(d, todayDayName);
            return (
              <button
                key={d}
                onClick={() => {
                  triggerHaptic('selection');
                  setSelectedDay(d);
                }}
                className={`px-3 py-1.5 rounded-[--radius-md] text-xs font-medium transition-all duration-[--duration-fast] ease-[--ease-spring-default] shrink-0 flex items-center gap-1.5 min-h-[44px] touch-manipulation cursor-pointer active:scale-95 ${
                  isSelected
                    ? 'bg-primary text-primary-foreground shadow-md font-semibold'
                    : 'bg-surface-2 text-muted-foreground hover:text-foreground hover:bg-surface-3'
                }`}
              >
                {d.slice(0, 3)}
                {isToday && (
                  <span className="w-1.5 h-1.5 rounded-full bg-success shadow-[0_0_6px_rgba(48,209,88,0.8)]" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 flex flex-col gap-2.5">
        {loading ? (
          <div className="flex flex-col gap-2.5">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="h-16 w-full bg-surface-2/40 rounded-[--radius-lg] shimmer"
              />
            ))}
          </div>
        ) : error ? (
          <EmptyState
            variant="error"
            description={error}
            action={{ label: 'Retry', onClick: loadSchedule }}
          />
        ) : activeDaySessions.length === 0 ? (
          <EmptyState
            icon={
              <CalendarIcon className="w-10 h-10 text-muted-foreground/30" />
            }
            title={`No classes on ${selectedDay}`}
            description={
              ['Saturday', 'Sunday'].includes(selectedDay)
                ? 'Enjoy your weekend!'
                : undefined
            }
          />
        ) : (
          activeDaySessions.map((s, idx) => {
            const rawSlot = String(s.timeSlot || '')
              .replace(/^Period\s*/i, '')
              .trim();
            const isTimestamp = rawSlot.includes(':');
            const displaySlot = isTimestamp ? rawSlot : `P${rawSlot}`;

            return (
              <div
                key={s.id || idx}
                className="flex flex-col gap-1.5 bg-surface-2/40 p-3.5 rounded-[--radius-lg] border border-border hover:border-primary/30 transition-all group touch-manipulation active:scale-[0.99]"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-mono font-bold bg-accent border border-primary/20 text-primary px-2 py-0.5 rounded-full">
                      {displaySlot}
                    </span>
                    {s.component && (
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                          s.component === 'Lecture'
                            ? 'bg-accent text-primary border border-primary/20'
                            : s.component === 'Practical'
                              ? 'bg-success/15 text-success border border-success/25'
                              : 'bg-warning/15 text-warning border border-warning/25'
                        }`}
                      >
                        {s.component}
                      </span>
                    )}
                  </div>
                  {s.room && (
                    <span className="flex items-center gap-1 text-[10px] font-medium text-success bg-success/15 border border-success/25 px-2 py-0.5 rounded-full">
                      <MapPin className="w-3 h-3" />
                      {s.room}
                    </span>
                  )}
                </div>
                <h4 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors leading-snug line-clamp-2 tracking-tight">
                  {getSubjectTitle(s.courseCode, s.courseTitle)}
                </h4>
                <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-border font-normal">
                  <span className="font-mono">
                    {getSubjectCode(s.courseCode, s.rawText)}
                  </span>
                  {s.faculty && (
                    <span className="flex items-center gap-1 truncate max-w-[180px]">
                      <User className="w-3 h-3 text-primary/70 shrink-0" />
                      {s.faculty}
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      <Link
        href="/dashboard/timetable"
        onClick={() => triggerHaptic('selection')}
        className="flex items-center justify-center gap-1.5 w-full p-3.5 text-xs font-semibold tracking-wider text-primary border-t border-border hover:bg-surface-2 transition-colors uppercase mt-auto touch-manipulation active:scale-95"
      >
        View Full Timetable <ChevronRight className="w-4 h-4" />
      </Link>
    </div>
  );
}

/* ── Current Courses Widget ── */
function CurrentCoursesWidget({
  activeYearId,
  activeSemId,
}: {
  activeYearId: string;
  activeSemId: string;
}) {
  const [courses, setCourses] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeYearId || !activeSemId) return;
    let mounted = true;

    async function loadCourses() {
      setLoading(true);
      try {
        const marksKey = [
          '/api/erp-proxy/marks',
          activeYearId,
          activeSemId,
        ] as const;
        const cachedMarks = getCachedValue<Record<string, unknown>[]>(marksKey);
        if (Array.isArray(cachedMarks) && cachedMarks.length > 0) {
          if (mounted) {
            setCourses(cachedMarks.slice(0, 6));
            setLoading(false);
            return;
          }
        }

        const marksRes = await fetch('/api/erp-proxy/marks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            academicYear: activeYearId,
            semesterId: activeSemId,
          }),
        }).catch(() => null);

        if (marksRes && marksRes.ok) {
          const marksData = await marksRes.json();
          if (
            marksData.success &&
            Array.isArray(marksData.data) &&
            marksData.data.length > 0
          ) {
            if (mounted) {
              setCourses(marksData.data.slice(0, 6));
              setLoading(false);
              return;
            }
          }
        }

        const cachedProf = getCachedValue<Record<string, unknown>>(
          '/api/erp-proxy/profile'
        );
        const profCourses = cachedProf?.courses;
        if (Array.isArray(profCourses) && profCourses.length > 0) {
          const mapped = profCourses
            .slice(0, 6)
            .map((c: Record<string, unknown>) => ({
              'Course Code': String(
                c.Coursecode || c.courseCode || c.code || 'N/A'
              )
                .toUpperCase()
                .trim(),
              'Course Name': String(
                c.Coursedesc || c.courseDesc || c.title || c.name || 'Course'
              ).trim(),
              'Evaluation Components': String(
                c.FacultyName || c.facultyName || c.faculty || 'Active Course'
              ).trim(),
            }));
          if (mounted) {
            setCourses(mapped);
            setLoading(false);
            return;
          }
        }
      } catch (e) {
        console.error('Failed to load courses:', e);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadCourses();
    return () => {
      mounted = false;
    };
  }, [activeYearId, activeSemId]);

  return (
    <div className="rounded-[--radius-2xl] apple-card flex flex-col h-full overflow-hidden shadow-xl border border-border">
      <div className="p-4 sm:p-5 border-b border-border flex justify-between items-center">
        <div className="flex items-center gap-2.5">
          <BookOpen className="w-5 h-5 text-primary" />
          <h3 className="text-sm font-semibold text-foreground tracking-tight font-heading">
            Current Courses
          </h3>
        </div>
        <Badge variant="success" dot className="text-[10px] apple-pill">
          Live
        </Badge>
      </div>

      <div className="flex-1 flex flex-col">
        {loading ? (
          <div className="flex justify-center items-center h-40">
            <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          </div>
        ) : courses.length === 0 ? (
          <EmptyState
            icon={<BookOpen className="w-10 h-10 text-muted-foreground/30" />}
            title="No active courses"
          />
        ) : (
          <div className="flex flex-col divide-y divide-white/6">
            {courses.map((course, idx) => {
              const keys = Object.keys(course);
              const codeKey =
                keys.find((k) => k.toLowerCase().includes('code')) ||
                'Course Code';
              const nameKey =
                keys.find(
                  (k) =>
                    k.toLowerCase().includes('name') ||
                    k.toLowerCase().includes('title')
                ) || 'Course Name';
              const compKey =
                keys.find(
                  (k) =>
                    k.toLowerCase().includes('eval') ||
                    k.toLowerCase().includes('component')
                ) || 'Evaluation Components';
              return (
                <div
                  key={idx}
                  className="p-4 flex items-start gap-3.5 hover:bg-surface-2 transition-colors"
                >
                  <div className="w-9 h-9 rounded-[--radius-lg] bg-primary/15 text-primary flex items-center justify-center shrink-0 border border-primary/25">
                    <span className="text-xs font-bold font-mono">
                      {idx + 1}
                    </span>
                  </div>
                  <div className="flex flex-col min-w-0 flex-1">
                    <p className="text-sm font-semibold text-foreground truncate tracking-tight">
                      {String(course[nameKey] || 'N/A')}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] font-mono bg-surface-2 text-muted-foreground px-2 py-0.5 rounded-full border border-border">
                        {String(course[codeKey] || 'N/A')}
                      </span>
                      <span className="text-xs text-muted-foreground truncate font-normal">
                        {String(course[compKey] || '')}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <Link
        href="/dashboard/marks"
        onClick={() => triggerHaptic('selection')}
        className="flex items-center justify-center gap-1.5 w-full p-3.5 text-xs font-semibold tracking-wider text-primary border-t border-border hover:bg-surface-2 transition-colors uppercase mt-auto touch-manipulation active:scale-95"
      >
        View All Courses <ChevronRight className="w-4 h-4" />
      </Link>
    </div>
  );
}
