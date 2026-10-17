import { useState, useEffect } from 'react';

const LS_ERP_YEAR = 'kl_erp_year';
const LS_ERP_SEM = 'kl_erp_sem';
const LS_ACADEMIC_YEARS = 'kl_erp_academic_years';
const LS_SEMESTERS = 'kl_erp_semesters';
const SS_ACADEMIC_YEARS = 'kl_erp_academic_years';
const SS_SEMESTERS = 'kl_erp_semesters';

export interface SemesterOption {
  value: string;
  label: string;
}

export function useAcademicSession() {
  const [years, setYears] = useState<SemesterOption[]>([]);
  const [semesters, setSemesters] = useState<SemesterOption[]>([]);
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedSem, setSelectedSem] = useState('');
  const [sessionError, setSessionError] = useState<string | null>(null);

  useEffect(() => {
    queueMicrotask(() => {
      try {
        const yStr =
          localStorage.getItem(LS_ACADEMIC_YEARS) ||
          localStorage.getItem(SS_ACADEMIC_YEARS) ||
          sessionStorage.getItem(SS_ACADEMIC_YEARS);
        const sStr =
          localStorage.getItem(LS_SEMESTERS) ||
          localStorage.getItem(SS_SEMESTERS) ||
          sessionStorage.getItem(SS_SEMESTERS);

        let parsedYears: SemesterOption[] = [];
        let parsedSems: SemesterOption[] = [];

        if (yStr) {
          try {
            parsedYears = JSON.parse(yStr);
          } catch (e) {
            console.error('Failed to parse academic years', e);
          }
        }

        if (sStr) {
          try {
            parsedSems = JSON.parse(sStr);
          } catch (e) {
            console.error('Failed to parse semesters', e);
          }
        }

        const DEFAULT_YEARS: SemesterOption[] = [
          { value: '2025-2026', label: '2025-2026' },
          { value: '2024-2025', label: '2024-2025' },
          { value: '2023-2024', label: '2023-2024' },
        ];
        const DEFAULT_SEMESTERS: SemesterOption[] = [
          { value: '1', label: 'Odd Semester' },
          { value: '2', label: 'Even Semester' },
          { value: '3', label: 'Summer Term' },
        ];

        const finalYears = parsedYears.length > 0 ? parsedYears : DEFAULT_YEARS;
        const finalSems =
          parsedSems.length > 0 ? parsedSems : DEFAULT_SEMESTERS;

        // Restore from localStorage or pick the first available option
        const savedYear = localStorage.getItem(LS_ERP_YEAR);
        const yearValid = finalYears.some((y) => y.value === savedYear);
        const targetYear =
          yearValid && savedYear
            ? savedYear
            : (finalYears.length > 0 ? finalYears[0].value : '2024-2025');

        const savedSem = localStorage.getItem(LS_ERP_SEM);
        const semValid = finalSems.some((s) => s.value === savedSem);
        const targetSem =
          semValid && savedSem
            ? savedSem
            : (finalSems.length > 0 ? finalSems[0].value : '1');

        setYears(finalYears);
        setSemesters(finalSems);
        if (targetYear) setSelectedYear(targetYear);
        if (targetSem) setSelectedSem(targetSem);
        setSessionError(null);
      } catch (e) {
        console.error('Session init error:', e);
        setSessionError(null);
      }
    });
  }, []);

  const handleYearChange = (val: string) => {
    setSelectedYear(val);
    localStorage.setItem(LS_ERP_YEAR, val);
  };

  const handleSemChange = (val: string) => {
    setSelectedSem(val);
    localStorage.setItem(LS_ERP_SEM, val);
  };

  return {
    years,
    semesters,
    selectedYear,
    selectedSem,
    handleYearChange,
    handleSemChange,
    sessionError,
  };
}
