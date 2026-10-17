'use client';

import { useState, useEffect } from 'react';

export type Locale = 'en' | 'te' | 'hi';

export interface LanguageInfo {
  code: Locale;
  name: string;
  nativeName: string;
  dir: 'ltr' | 'rtl';
  flag: string;
}

export const SUPPORTED_LANGUAGES: LanguageInfo[] = [
  {
    code: 'en',
    name: 'English',
    nativeName: 'English',
    dir: 'ltr',
    flag: '🇺🇸',
  },
  { code: 'te', name: 'Telugu', nativeName: 'తెలుగు', dir: 'ltr', flag: '🇮🇳' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', dir: 'ltr', flag: '🇮🇳' },
];

export const TRANSLATIONS: Record<Locale, Record<string, string>> = {
  en: {
    dashboard: 'Dashboard',
    attendance: 'Attendance',
    timetable: 'Timetable',
    marks: 'Marks',
    profile: 'Profile',
    fee: 'Fee Details',
    circulars: 'Circulars',
    hostels: 'Hostel Info',
    library: 'Library',
    examSeating: 'Exam Seating',
    tools: 'Tools',
    compliance: 'Privacy & Accessibility Compliance',
    privacyAndData: 'Privacy & Data',
    accessibility: 'Accessibility',
    exportData: 'Export My Data',
    eraseData: 'Erase All Data',
    signIn: 'Sign In',
    securityCode: 'Security Code',
    studentId: 'Student ID / Username',
    password: 'Password',
    rememberMe: 'Remember me',
    overallAttendance: 'Overall Attendance',
    cgpa: 'Current CGPA',
    totalAttended: 'Attended Classes',
    totalConducted: 'Total Conducted',
    language: 'Language',
    rtlSupport: 'RTL Support',
    theme: 'Theme',
    logout: 'Log Out',
    close: 'Close',
    save: 'Save',
    search: 'Search...',
    noRecords: 'No records found.',
  },
  te: {
    dashboard: 'డ్యాష్‌బోర్డ్',
    attendance: 'హాజరు',
    timetable: 'సమయ పట్టిక',
    marks: 'మార్కులు',
    profile: 'ప్రొఫైల్',
    fee: 'ఫీజు వివరాలు',
    circulars: 'సర్క్యులర్లు',
    hostels: 'హాస్టల్ సమాచారం',
    library: 'లైబ్రరీ',
    examSeating: 'పరీక్షా సీటింగ్',
    tools: 'సాధనాలు',
    compliance: 'గోప్యత & ప్రాప్యత సమ్మతి',
    privacyAndData: 'గోప్యత & డేటా',
    accessibility: 'ప్రాప్యత',
    exportData: 'నా డేటాను ఎగుమతి చేయండి',
    eraseData: 'మొత్తం డేటాను తొలగించండి',
    signIn: 'ప్రవేశించండి',
    securityCode: 'భద్రతా కోడ్',
    studentId: 'విద్యార్థి ఐడి',
    password: 'పాస్‌వర్డ్',
    rememberMe: 'నన్ను గుర్తుంచుకో',
    overallAttendance: 'మొత్తం హాజరు',
    cgpa: 'ప్రస్తుత CGPA',
    totalAttended: 'హాజరైన తరగతులు',
    totalConducted: 'నిర్వహించిన మొత్తం',
    language: 'భాష',
    rtlSupport: 'RTL మద్దతు',
    theme: 'థీమ్',
    logout: 'లాగ్ అవుట్',
    close: 'మూసివేయి',
    save: 'భద్రపరుచు',
    search: 'శోధించండి...',
    noRecords: 'ఎటువంటి రికార్డులు కనుగొనబడలేదు.',
  },
  hi: {
    dashboard: 'डैशबोर्ड',
    attendance: 'उपस्थिति',
    timetable: 'समय सारणी',
    marks: 'अंक',
    profile: 'प्रोफाइल',
    fee: 'शुल्क विवरण',
    circulars: 'परिपत्र',
    hostels: 'छात्रावास जानकारी',
    library: 'पुस्तकालय',
    examSeating: 'परीक्षा बैठक व्यवस्था',
    tools: 'उपकरण',
    compliance: 'गोपनीयता और पहुंच अनुपालन',
    privacyAndData: 'गोपनीयता और डेटा',
    accessibility: 'पहुंच',
    exportData: 'मेरा डेटा निर्यात करें',
    eraseData: 'सभी डेटा मिटाएं',
    signIn: 'साइन इन करें',
    securityCode: 'सुरक्षा कोड',
    studentId: 'छात्र आईडी / उपयोगकर्ता नाम',
    password: 'पासवर्ड',
    rememberMe: 'मुझे याद रखें',
    overallAttendance: 'कुल उपस्थिति',
    cgpa: 'वर्तमान सीजीपीए',
    totalAttended: 'उपस्थित कक्षाएं',
    totalConducted: 'कुल कक्षाएं',
    language: 'भाषा',
    rtlSupport: 'आरटीएल समर्थन',
    theme: 'थीम',
    logout: 'लॉग आउट',
    close: 'बंद करें',
    save: 'सहेजें',
    search: 'खोजें...',
    noRecords: 'कोई रिकॉर्ड नहीं मिला।',
  },
  };

const listeners = new Set<(locale: Locale) => void>();

export function getLocale(): Locale {
  if (typeof window === 'undefined') return 'en';
  try {
    const stored = localStorage.getItem('kl_locale') as Locale;
    if (stored && TRANSLATIONS[stored]) return stored;
  } catch {}
  return 'en';
}

export function setLocale(locale: Locale): void {
  if (!TRANSLATIONS[locale]) return;
  if (typeof window !== 'undefined') {
    try {
      localStorage.setItem('kl_locale', locale);
      const langInfo = SUPPORTED_LANGUAGES.find((l) => l.code === locale);
      const dir = langInfo?.dir || 'ltr';
      document.documentElement.setAttribute('lang', locale);
      document.documentElement.setAttribute('dir', dir);
      if (dir === 'rtl') {
        document.documentElement.classList.add('rtl');
      } else {
        document.documentElement.classList.remove('rtl');
      }
    } catch {}
  }
  listeners.forEach((l) => l(locale));
}

export function useI18n() {
  const [locale, setLocaleState] = useState<Locale>(() => getLocale());

  useEffect(() => {
    const handler = (newLoc: Locale) => setLocaleState(newLoc);
    listeners.add(handler);
    return () => {
      listeners.delete(handler);
    };
  }, []);

  const t = (key: string, defaultText?: string): string => {
    return (
      TRANSLATIONS[locale]?.[key] || TRANSLATIONS.en[key] || defaultText || key
    );
  };

  const changeLocale = (newLocale: Locale) => {
    setLocale(newLocale);
    setLocaleState(newLocale);
  };

  const currentLanguage =
    SUPPORTED_LANGUAGES.find((l) => l.code === locale) ||
    SUPPORTED_LANGUAGES[0];
  const isRtl = currentLanguage.dir === 'rtl';

  return {
    locale,
    t,
    changeLocale,
    currentLanguage,
    isRtl,
    supportedLanguages: SUPPORTED_LANGUAGES,
  };
}
