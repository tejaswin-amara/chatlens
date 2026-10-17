'use client';

import { useState } from 'react';
import { useAcademicSession } from '@/hooks/useAcademicSession';

import { exportTableToCSV } from '@/lib/utils';
import {
  isSameDay,
  normalizeSlotKey,
  ParsedTimetable,
} from '@/lib/timetable-parser';
import { getSubjectTitle, getSubjectCode } from '@/lib/course-utils';
import {
  LayoutGrid,
  List,
  Search,
  CalendarOff,
  AlertCircle,
  ChevronDown,
  Download,
  MapPin,
  RefreshCw,
  Filter,
} from '@/components/ui/icons';

import { useTimetable } from '@/hooks/useTimetable';
import { triggerHaptic } from '@/lib/fluid-motion';

function parseTimeSlotToMinutes(slot: string): number {
  if (!slot) return 9999;
  const key = normalizeSlotKey(slot);
  const num = Number(key);
  if (!isNaN(num)) {
    return num * 60;
  }

  const match = slot.match(/(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
  if (match) {
    let hours = parseInt(match[1], 10);
    const minutes = parseInt(match[2], 10);
    const ampm = match[3]?.toUpperCase();

    if (ampm === 'PM' && hours < 12) {
      hours += 12;
    } else if (ampm === 'AM' && hours === 12) {
      hours = 0;
    }
    return hours * 60 + minutes;
  }

  return 9999;
}

function getSlotsToRender(parsedTT: ParsedTimetable | null): string[] {
  if (!parsedTT || !parsedTT.timeSlotsPresent) {
    return Array.from({ length: 8 }, (_, i) => String(i + 1));
  }

  const sortedTimeSlots = [...parsedTT.timeSlotsPresent].sort((a, b) => {
    const keyA = normalizeSlotKey(a);
    const keyB = normalizeSlotKey(b);
    const numA = Number(keyA);
    const numB = Number(keyB);
    if (!isNaN(numA) && !isNaN(numB) && numA !== numB) {
      return numA - numB;
    }
    const minA = parseTimeSlotToMinutes(a);
    const minB = parseTimeSlotToMinutes(b);
    if (minA !== minB) {
      return minA - minB;
    }
    return a.localeCompare(b);
  });

  const numericSlots = sortedTimeSlots
    .map((s) => Number(normalizeSlotKey(s)))
    .filter((n) => !isNaN(n) && n > 0);

  if (numericSlots.length > 0) {
    const maxNum = Math.max(...numericSlots, 8);
    const minNum = Math.min(...numericSlots, 1);
    const fullRange: string[] = [];
    for (let i = minNum; i <= maxNum; i++) {
      fullRange.push(String(i));
    }
    const nonNumeric = sortedTimeSlots.filter((s) =>
      isNaN(Number(normalizeSlotKey(s)))
    );
    return [...fullRange, ...nonNumeric];
  } else if (sortedTimeSlots.length > 0) {
    return sortedTimeSlots;
  } else {
    return Array.from({ length: 8 }, (_, i) => String(i + 1));
  }
}

export default function TimetablePage() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedDayFilter, setSelectedDayFilter] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState('');

  const {
    years,
    semesters,
    selectedYear,
    selectedSem,
    handleYearChange,
    handleSemChange,
    sessionError,
  } = useAcademicSession();

  const {
    data: parsedTT,
    isLoading: loading,
    error: fetchError,
    mutate,
  } = useTimetable(selectedYear, selectedSem);
  const displayError = (fetchError ? fetchError.message : null) || sessionError;

  const daysList = [
    'All',
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ];

  const filteredSessions = (parsedTT?.sessions || []).filter((session) => {
    const matchesDay =
      selectedDayFilter === 'All' || isSameDay(session.day, selectedDayFilter);
    const q = searchQuery.toLowerCase().trim();
    const matchesSearch =
      !q ||
      session.courseCode.toLowerCase().includes(q) ||
      session.courseTitle.toLowerCase().includes(q) ||
      session.room.toLowerCase().includes(q) ||
      session.faculty.toLowerCase().includes(q) ||
      session.timeSlot.toLowerCase().includes(q) ||
      session.day.toLowerCase().includes(q);

    return matchesDay && matchesSearch;
  });

  const handleExportCSV = () => {
    triggerHaptic('light');
    if (!parsedTT || parsedTT.sessions.length === 0) return;
    const exportData = filteredSessions.map((s) => ({
      Day: s.day,
      'Time Slot': s.timeSlot,
      'Course Code': s.courseCode,
      'Course Title': s.courseTitle,
      Room: s.room,
      Faculty: s.faculty,
    }));
    exportTableToCSV(
      exportData,
      `Timetable_${selectedYear}_${selectedSem}.csv`
    );
  };

  return (
    <div className="flex flex-col gap-6 w-full animate-spring-up">
      {/* Header Bar */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <div>
          <h2 className="text-3xl font-semibold tracking-[-0.025em] text-foreground font-heading">
            Student Timetable
          </h2>
          <p className="text-xs text-muted-foreground/90 mt-1 font-normal">
            Interactive weekly schedule synced securely from the ERP.
          </p>
        </div>

        {/* Controls: Year, Semester, View Toggle, Export */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center apple-card p-1 rounded-[--radius-lg] shadow-md border border-border">
            <button
              onClick={() => {
                triggerHaptic('selection');
                setViewMode('grid');
              }}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-[--radius-md] text-xs font-semibold transition-all duration-[--duration-fast] ease-[--ease-spring-default] min-h-[44px] touch-manipulation cursor-pointer ${
                viewMode === 'grid'
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <LayoutGrid className="w-4 h-4" />
              Grid
            </button>
            <button
              onClick={() => {
                triggerHaptic('selection');
                setViewMode('list');
              }}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-[--radius-md] text-xs font-semibold transition-all duration-[--duration-fast] ease-[--ease-spring-default] min-h-[44px] touch-manipulation cursor-pointer ${
                viewMode === 'list'
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <List className="w-4 h-4" />
              List
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2 apple-card p-1.5 rounded-[--radius-lg] shadow-md border border-border">
            <div className="relative">
              <select
                aria-label="Filter by year"
                className="appearance-none bg-transparent border-none rounded-[--radius-md] pl-3 pr-8 py-2 text-xs font-semibold text-foreground focus:outline-hidden cursor-pointer min-h-[44px]"
                value={selectedYear}
                onChange={(e) => {
                  triggerHaptic('selection');
                  handleYearChange(e.target.value);
                }}
              >
                {years.map((y) => (
                  <option
                    key={y.value}
                    value={y.value}
                    className="bg-surface-2 text-foreground"
                  >
                    {y.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
            </div>
            <div className="h-4 w-px bg-surface-3"></div>
            <div className="relative">
              <select
                aria-label="Filter by semester"
                className="appearance-none bg-transparent border-none rounded-[--radius-md] pl-3 pr-8 py-2 text-xs font-semibold text-foreground focus:outline-hidden cursor-pointer min-h-[44px]"
                value={selectedSem}
                onChange={(e) => {
                  triggerHaptic('selection');
                  handleSemChange(e.target.value);
                }}
              >
                {semesters.map((s) => (
                  <option
                    key={s.value}
                    value={s.value}
                    className="bg-surface-2 text-foreground"
                  >
                    {s.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
            </div>
          </div>

          <button
            onClick={handleExportCSV}
            disabled={!parsedTT || parsedTT.sessions.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 apple-card hover:bg-surface-2 rounded-[--radius-lg] text-xs font-semibold text-foreground transition-all disabled:opacity-40 min-h-[44px] cursor-pointer touch-manipulation active:scale-95 border border-border"
          >
            <Download className="w-4 h-4 text-primary" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 apple-card p-3 rounded-[--radius-2xl] shadow-lg border border-border">
        {/* Day Filter Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto custom-scrollbar p-1 bg-surface-2/40 rounded-[--radius-lg] border border-border/60">
          <Filter className="w-3.5 h-3.5 text-muted-foreground ml-1 mr-1 shrink-0" />
          {daysList.map((day) => (
            <button
              key={day}
              onClick={() => {
                triggerHaptic('selection');
                setSelectedDayFilter(day);
              }}
              className={`px-3 py-1.5 rounded-[--radius-md] text-xs font-medium whitespace-nowrap transition-all duration-[--duration-fast] ease-[--ease-spring-default] min-h-[44px] touch-manipulation cursor-pointer active:scale-95 ${
                selectedDayFilter === day
                  ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                  : 'text-muted-foreground hover:text-foreground hover:bg-surface-3'
              }`}
            >
              {day}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64 shrink-0">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            placeholder="Search course, room, faculty..."
            className="w-full bg-surface-2/60 border border-border rounded-[--radius-lg] pl-9 pr-3 py-2 text-xs text-foreground focus:outline-hidden focus:border-primary/50 transition-all placeholder:text-muted-foreground font-normal"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Main Content Card */}
      <div className="rounded-[--radius-2xl] border border-border apple-card shadow-2xl overflow-hidden min-h-[320px] flex flex-col">
        {loading ? (
          <div className="p-8 flex flex-col gap-6">
            <div className="flex gap-4">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className="h-8 w-24 bg-surface-2/40 rounded-[--radius-md] shimmer"
                ></div>
              ))}
            </div>
            <div className="flex flex-col gap-4">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className="h-16 w-full bg-surface-2/30 rounded-[--radius-lg] shimmer"
                ></div>
              ))}
            </div>
          </div>
        ) : displayError ? (
          <div className="flex flex-col items-center justify-center flex-1 p-12 text-center my-auto">
            <div className="w-16 h-16 rounded-[--radius-2xl] bg-destructive/15 border border-destructive/25 flex items-center justify-center text-destructive mb-4 shadow-inner">
              <AlertCircle className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2 tracking-tight">
              Failed to Sync Timetable
            </h3>
            <p className="text-xs text-muted-foreground max-w-md leading-relaxed mb-6 font-normal">
              {displayError}
            </p>
            <button
              onClick={() => {
                triggerHaptic('light');
                mutate();
              }}
              className="px-5 py-2.5 bg-primary hover:bg-primary/90 text-xs font-semibold text-primary-foreground rounded-[--radius-lg] transition-all shadow-lg flex items-center gap-2 cursor-pointer touch-manipulation active:scale-95 min-h-[44px]"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Retry Sync
            </button>
          </div>
        ) : !parsedTT || parsedTT.sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center flex-1 p-12 text-center my-auto">
            <div className="w-16 h-16 rounded-[--radius-2xl] bg-surface-2/60 border border-border flex items-center justify-center text-muted-foreground mb-4">
              <CalendarOff className="w-8 h-8 text-muted-foreground/50" />
            </div>
            <h3 className="text-base font-semibold text-foreground mb-1 tracking-tight">
              No Timetable Data Found
            </h3>
            <p className="text-xs text-muted-foreground max-w-sm font-normal">
              There are no class sessions available for the selected academic
              term.
            </p>
          </div>
        ) : viewMode === 'grid' ? (
          /* Horizontal Academic Matrix Grid View Mode */
          <div className="p-4 sm:p-6 overflow-x-auto custom-scrollbar flex-1 w-full">
            {parsedTT.daysPresent.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground text-sm">
                No matching sessions for the selected day filter.
              </div>
            ) : (
              <div className="w-full min-w-max flex flex-col gap-6">
                <div className="bg-surface-2/30 border border-border rounded-[--radius-2xl] overflow-hidden shadow-xl">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-surface-2/60 border-b border-border text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        <th
                          scope="col"
                          className="p-4 sticky left-0 z-20 bg-surface-1/95 backdrop-blur-md min-w-[120px] border-r border-border text-primary text-center"
                        >
                          Day / Period
                        </th>
                        {getSlotsToRender(parsedTT).map((periodNum) => (
                          <th
                            scope="col"
                            key={periodNum}
                            className="p-3.5 text-center min-w-[170px] border-r border-border last:border-r-0 text-foreground font-semibold"
                          >
                            {periodNum.length < 3 &&
                            !periodNum.toLowerCase().includes('p')
                              ? `Period ${periodNum}`
                              : periodNum}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/6">
                      {(() => {
                        const allDays = [
                          'Monday',
                          'Tuesday',
                          'Wednesday',
                          'Thursday',
                          'Friday',
                          'Saturday',
                          'Sunday',
                        ];
                        const daysToRender = allDays.filter((day) => {
                          if (selectedDayFilter !== 'All') {
                            return day === selectedDayFilter;
                          }
                          if (day === 'Sunday') {
                            return parsedTT.daysPresent.some((d) =>
                              isSameDay(d, 'Sunday')
                            );
                          }
                          return true;
                        });

                        const slotsToRender = getSlotsToRender(parsedTT);

                        return daysToRender.map((day) => {
                          return (
                            <tr
                              key={day}
                              className="hover:bg-surface-2/70 transition-colors"
                            >
                              {/* Sticky Day Column */}
                              <th
                                scope="row"
                                className="p-4 sticky left-0 z-10 bg-surface-1/95 backdrop-blur-md font-bold text-xs text-foreground border-r border-border text-center whitespace-nowrap"
                              >
                                {day}
                              </th>

                              {/* Period Columns for this Day */}
                              {slotsToRender.map((periodNum) => {
                                const matchingSessions = (
                                  parsedTT.matrixGrid[day]?.[periodNum] || []
                                ).filter((session) => {
                                  if (!searchQuery.trim()) return true;
                                  const q = searchQuery.toLowerCase().trim();
                                  return (
                                    session.courseCode
                                      .toLowerCase()
                                      .includes(q) ||
                                    session.courseTitle
                                      .toLowerCase()
                                      .includes(q) ||
                                    session.room.toLowerCase().includes(q) ||
                                    session.faculty.toLowerCase().includes(q)
                                  );
                                });

                                return (
                                  <td
                                    key={periodNum}
                                    className="p-2 border-r border-border last:border-r-0 align-top min-w-[170px]"
                                  >
                                    {matchingSessions.length > 0 ? (
                                      <div className="flex flex-col gap-2 h-full">
                                        {matchingSessions.map(
                                          (session, sIdx) => {
                                            const subjectTitle =
                                              getSubjectTitle(
                                                session.courseCode,
                                                session.courseTitle
                                              );
                                            const subjectCode = getSubjectCode(
                                              session.courseCode,
                                              session.rawText
                                            );

                                            return (
                                              <div
                                                key={
                                                  session.id ||
                                                  `${session.courseCode}-${sIdx}`
                                                }
                                                className="bg-surface-2/60 border border-border hover:border-primary/40 p-3 rounded-[--radius-lg] flex flex-col justify-between gap-2 shadow-md transition-all overflow-hidden min-h-[96px] group touch-manipulation active:scale-[0.98]"
                                              >
                                                <div className="flex items-center justify-between gap-1">
                                                  {session.component && (
                                                    <span
                                                      className={`text-[9px] font-extrabold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                                                        session.component ===
                                                        'Lecture'
                                                          ? 'bg-info/10 text-info border border-info/20'
                                                          : session.component ===
                                                              'Practical'
                                                            ? 'bg-success/10 text-success border border-success/20'
                                                            : session.component ===
                                                                'Skill'
                                                              ? 'bg-primary/10 text-primary border border-primary/20'
                                                              : 'bg-warning/10 text-warning border border-warning/20'
                                                      }`}
                                                    >
                                                      {session.component}
                                                    </span>
                                                  )}
                                                  {session.section && (
                                                    <span className="text-[9px] font-mono bg-surface-3 text-muted-foreground px-1.5 py-0.5 rounded-full">
                                                      {session.section}
                                                    </span>
                                                  )}
                                                </div>

                                                <h5 className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors leading-snug line-clamp-2 overflow-hidden tracking-tight">
                                                  {subjectTitle}
                                                </h5>

                                                <div className="flex items-center justify-between gap-1 text-[10px] text-muted-foreground pt-1.5 border-t border-border mt-auto">
                                                  <span className="font-mono text-muted-foreground font-medium truncate">
                                                    {subjectCode}
                                                  </span>
                                                  {session.room && (
                                                    <span className="text-success font-semibold flex items-center gap-0.5 shrink-0 ml-auto">
                                                      <MapPin className="w-2.5 h-2.5" />
                                                      {session.room}
                                                    </span>
                                                  )}
                                                </div>
                                              </div>
                                            );
                                          }
                                        )}
                                      </div>
                                    ) : (
                                      <div className="h-24 rounded-[--radius-lg] border border-dashed border-border flex items-center justify-center text-muted-foreground/30 text-xs">
                                        -
                                      </div>
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        });
                      })()}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* List View Mode */
          <div className="p-6 overflow-x-auto custom-scrollbar flex-1">
            {filteredSessions.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground text-sm">
                No matching sessions found for your filter/search criteria.
              </div>
            ) : (
              <table className="w-full text-left whitespace-nowrap border-separate border-spacing-y-2">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border">
                      Day
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border">
                      Period / Slot
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border">
                      Course Code
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border">
                      Course Title
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border">
                      Component & Section
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border">
                      Venue / Room
                    </th>
                    <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border">
                      Faculty
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSessions.map((session, idx) => (
                    <tr
                      key={session.id || idx}
                      className="group bg-surface-2/40 hover:bg-surface-2/70 transition-colors"
                    >
                      <td className="px-4 py-3.5 text-xs font-semibold text-primary first:rounded-l-[--radius-lg] border-y border-transparent">
                        {session.day}
                      </td>
                      <td className="px-4 py-3.5 text-xs font-mono text-muted-foreground border-y border-transparent">
                        <span className="bg-primary/15 border border-primary/25 text-primary px-2 py-0.5 rounded-full">
                          Period{' '}
                          {String(session.timeSlot || '')
                            .replace(/^Period\s*/i, '')
                            .trim()}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-xs font-mono text-muted-foreground border-y border-transparent">
                        {getSubjectCode(session.courseCode, session.rawText) ||
                          'N/A'}
                      </td>
                      <td className="px-4 py-3.5 text-sm font-semibold text-foreground border-y border-transparent max-w-xs truncate tracking-tight">
                        {getSubjectTitle(
                          session.courseCode,
                          session.courseTitle
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-xs border-y border-transparent">
                        <div className="flex items-center gap-1.5">
                          {session.component && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-primary/20 text-primary">
                              {session.component}
                            </span>
                          )}
                          {session.section && (
                            <span className="text-[10px] font-mono bg-surface-3 text-muted-foreground px-1.5 py-0.5 rounded-full">
                              {session.section}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-xs font-semibold text-success border-y border-transparent">
                        {session.room ? (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3.5 h-3.5" />
                            {session.room}
                          </span>
                        ) : (
                          'N/A'
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-xs text-muted-foreground border-y border-transparent last:rounded-r-[--radius-lg]">
                        {session.faculty || 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
