'use client';

/* eslint-disable @next/next/no-img-element */

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  User,
  CheckSquare,
  Star,
  Calendar,
  CreditCard,
  Megaphone,
  Building2,
  BookOpen,
  LogOut,
  Menu,
  Bell,
  MoreHorizontal,
  X,
  ChevronLeft,
  MapPin,
} from '@/components/ui/icons';
import { AICopilot } from '@/components/ai/AICopilot';
import { Badge } from '@/components/ui/badge';
import { triggerHaptic } from '@/lib/fluid-motion';
import { prefetchAllUserData } from '@/lib/data-prefetcher';
import { useI18n } from '@/lib/i18n';
import { LanguageSelector } from '@/components/ui/LanguageSelector';

function ProfileAvatar({
  user,
  className = '',
  size = 'md',
}: {
  user: { id: string; initials: string; photoUrl: string };
  className?: string;
  size?: 'sm' | 'md';
}) {
  const dimensions =
    size === 'sm' ? 'h-8 w-8 text-[10px]' : 'h-10 w-10 text-xs';
  const photoSrc = useMemo(() => {
    if (!user.photoUrl)
      return `/api/fetch-photo?id=${encodeURIComponent(user.id)}`;
    if (
      /^data:image\/(png|jpeg|jpg|webp|gif);base64,[A-Za-z0-9+/=]+$/i.test(
        user.photoUrl
      )
    )
      return user.photoUrl;
    const cleanPath = user.photoUrl.startsWith('/')
      ? user.photoUrl
      : `/${user.photoUrl}`;
    return `/api/fetch-photo?path=${encodeURIComponent(cleanPath)}`;
  }, [user.photoUrl, user.id]);

  return (
    <div
      className={`${dimensions} relative flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-surface-2 font-bold shadow-xs ${className}`}
    >
      {user.id !== 'Student ID' && user.id !== 'Loading...' && (
        <img
          src={photoSrc}
          alt="Profile"
          className="absolute inset-0 z-10 h-full w-full object-cover"
          onError={(event) => {
            event.currentTarget.style.display = 'none';
          }}
        />
      )}
      <span className="relative z-0 text-primary" suppressHydrationWarning>
        {user.initials}
      </span>
    </div>
  );
}

export default function Navigation({
  children,
}: {
  children: React.ReactNode;
}) {
  const { t } = useI18n();
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [user, setUser] = useState({
    name: 'Student',
    initials: 'ST',
    id: 'Loading...',
    photoUrl: '',
  });

  const allNavItems = useMemo(
    () => [
      {
        href: '/dashboard',
        label: t('dashboard', 'Overview'),
        icon: LayoutDashboard,
      },
      {
        href: '/dashboard/attendance',
        label: t('attendance', 'Attendance'),
        icon: CheckSquare,
      },
      {
        href: '/dashboard/timetable',
        label: t('timetable', 'Timetable'),
        icon: Calendar,
      },
      { href: '/dashboard/marks', label: t('marks', 'Marks'), icon: Star },
      {
        href: '/dashboard/profile',
        label: t('profile', 'Profile'),
        icon: User,
      },
      {
        href: '/dashboard/fee',
        label: t('fee', 'Fee details'),
        icon: CreditCard,
      },
      {
        href: '/dashboard/exam-seating',
        label: t('examSeating', 'Exam seating'),
        icon: MapPin,
      },
      {
        href: '/dashboard/circulars',
        label: t('circulars', 'Circulars'),
        icon: Megaphone,
      },
      {
        href: '/dashboard/hostels',
        label: t('hostels', 'Hostel info'),
        icon: Building2,
      },
      {
        href: '/dashboard/library',
        label: t('library', 'Library'),
        icon: BookOpen,
      },
      {
        href: '/dashboard/tools',
        label: t('tools', 'Tools'),
        icon: CheckSquare,
      },
    ],
    [t]
  );

  const bottomItems = allNavItems.slice(0, 4);
  const overflowItems = allNavItems.slice(4);
  const isActive = (href: string) =>
    pathname === href || (href !== '/dashboard' && pathname.startsWith(href));
  const pageTitle =
    allNavItems.find((item) => item.href === pathname)?.label ||
    allNavItems.find(
      (item) => item.href !== '/dashboard' && pathname.startsWith(item.href)
    )?.label ||
    'Overview';

  useEffect(() => {
    void prefetchAllUserData();
    queueMicrotask(() => {
      const cachedName = localStorage.getItem('kl_student_name');
      const cachedPhoto = localStorage.getItem('kl_student_photo') || '';
      const name = cachedName || 'Student';
      const id = localStorage.getItem('studentId') || 'Student ID';
      const initials =
        name === 'Student'
          ? 'ST'
          : name
              .split(' ')
              .map((part) => part[0])
              .join('')
              .slice(0, 2)
              .toUpperCase();
      setUser({ name, initials, id, photoUrl: cachedPhoto });
      if (localStorage.getItem('kl_sidebar_collapsed') === 'true')
        setCollapsed(true);
    });

    const handleProfileUpdate = () => {
      const updatedName = localStorage.getItem('kl_student_name') || 'Student';
      const updatedPhoto = localStorage.getItem('kl_student_photo') || '';
      const id = localStorage.getItem('studentId') || 'Student ID';
      const initials =
        updatedName === 'Student'
          ? 'ST'
          : updatedName
              .split(' ')
              .map((part) => part[0])
              .join('')
              .slice(0, 2)
              .toUpperCase();
      setUser({ name: updatedName, initials, id, photoUrl: updatedPhoto });
    };

    window.addEventListener('kl_profile_updated', handleProfileUpdate);
    return () =>
      window.removeEventListener('kl_profile_updated', handleProfileUpdate);
  }, []);

  const handleSignOut = async () => {
    triggerHaptic('warning');
    try {
      await fetch('/api/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
    } catch {}
    sessionStorage.clear();
    // ponytail: prefix-sweep instead of maintaining a key list; upgrade to namespace if storage grows
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith('kl_') || key === 'studentId' || key === 'remember_username')) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach((key) => localStorage.removeItem(key));
    router.push('/');
  };

  const toggleCollapse = () => {
    triggerHaptic('selection');
    setCollapsed((current) => {
      const next = !current;
      localStorage.setItem('kl_sidebar_collapsed', String(next));
      return next;
    });
  };

  const renderNavLink = (
    item: (typeof allNavItems)[number],
    compact = false,
    closeDrawer?: () => void
  ) => {
    const active = isActive(item.href);
    const Icon = item.icon;
    return (
      <Link
        key={item.href}
        href={item.href}
        aria-current={active ? 'page' : undefined}
        title={compact ? item.label : undefined}
        onClick={() => {
          triggerHaptic('selection');
          closeDrawer?.();
        }}
        className={`group flex min-h-[44px] items-center gap-3 rounded-[--radius-md] text-sm font-semibold transition-[background-color,color,transform] duration-[--duration-fast] active:scale-[0.98] ${compact ? 'mx-1 justify-center px-0' : 'px-3'} ${active ? 'bg-primary text-primary-foreground shadow-sm shadow-primary/20' : 'text-muted-foreground hover:bg-surface-2 hover:text-foreground'}`}
      >
        <Icon
          className={`h-[18px] w-[18px] shrink-0 ${active ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-primary'}`}
        />
        {!compact && <span className="truncate">{item.label}</span>}
      </Link>
    );
  };

  return (
    <div className="relative h-[100dvh] min-h-[100dvh] overflow-hidden bg-background text-foreground">
      <header className="apple-chrome fixed inset-x-0 top-0 z-40 flex h-[calc(var(--header-height)+env(safe-area-inset-top,0px))] items-center justify-between border-b px-4 pt-[env(safe-area-inset-top,0px)] lg:hidden">
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              triggerHaptic('selection');
              setSidebarOpen(true);
            }}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-muted-foreground hover:bg-surface-2 hover:text-foreground"
            aria-label="Open navigation menu"
            aria-expanded={sidebarOpen}
          >
            <Menu className="h-5 w-5" />
          </button>
          <Link
            href="/dashboard"
            className="flex items-center gap-2"
            onClick={() => triggerHaptic('selection')}
          >
            <img
              src="/logo.webp"
              alt="KL"
              className="h-7 w-auto rounded-md bg-surface-1 object-contain"
            />
            <span className="font-heading text-sm font-bold tracking-tight">
              KL Sync
            </span>
          </Link>
        </div>
        <div className="flex items-center gap-1">
          <LanguageSelector />
          <Link
            href="/dashboard/profile"
            aria-label="Student profile"
            className="flex min-h-[44px] min-w-[44px] items-center justify-center"
          >
            <ProfileAvatar user={user} size="sm" />
          </Link>
        </div>
      </header>

      {sidebarOpen && (
        <>
          <div
            className="animate-fade-in fixed inset-0 z-50 bg-slate-950/25 backdrop-blur-sm lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
          <aside
            id="mobile-sidebar-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            onKeyDown={(e) => {
              if (e.key === 'Escape') setSidebarOpen(false);
            }}
            className="apple-chrome animate-drawer-enter fixed inset-y-0 left-0 z-50 flex w-[min(86vw,320px)] flex-col border-r p-4 lg:hidden"
          >
            <div className="flex items-center justify-between border-b pb-4">
              <Link href="/dashboard" className="flex items-center gap-2.5">
                <img
                  src="/logo.webp"
                  alt="KL"
                  className="h-8 rounded-md bg-surface-1"
                />
                <span className="font-heading font-bold">KL Sync</span>
              </Link>
              <button
                onClick={() => setSidebarOpen(false)}
                className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-muted-foreground hover:bg-surface-2"
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex items-center gap-3 border-b py-4">
              <ProfileAvatar user={user} />
              <div className="min-w-0">
                <p className="truncate text-sm font-bold">{user.name}</p>
                <p className="truncate font-mono text-[11px] text-muted-foreground">
                  {user.id}
                </p>
              </div>
            </div>
            <nav className="custom-scrollbar flex-1 overflow-y-auto py-2">
              {allNavItems.map((item) =>
                renderNavLink(item, false, () => setSidebarOpen(false))
              )}
            </nav>
            <div className="border-t pt-3">
              <button
                onClick={handleSignOut}
                className="flex min-h-[44px] w-full items-center gap-3 rounded-[--radius-md] px-3 text-sm font-semibold text-destructive hover:bg-error/10"
              >
                <LogOut className="h-[18px] w-[18px]" />
                {t('logout', 'Sign out')}
              </button>
            </div>
          </aside>
        </>
      )}

      <aside
        className={`apple-chrome bg-surface-1 fixed inset-y-0 left-0 z-30 hidden flex-col border-r transition-[width] duration-[var(--duration-normal)] lg:flex ${collapsed ? 'w-[var(--sidebar-collapsed)]' : 'w-[var(--sidebar-width)]'}`}
      >
        <div className="flex h-[var(--header-height)] items-center justify-between border-b px-4">
          {collapsed ? (
            <button
              onClick={toggleCollapse}
              className="mx-auto flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl bg-surface-2 text-primary hover:bg-surface-3 transition-colors"
              aria-label="Expand sidebar"
              title="Expand sidebar"
            >
              <Menu className="h-5 w-5" />
            </button>
          ) : (
            <>
              <Link href="/dashboard" className="flex items-center gap-2.5">
                <img
                  src="/logo.webp"
                  alt="KL"
                  className="h-8 max-w-[120px] rounded-md bg-surface-1 object-contain"
                />
                <span className="font-heading text-base font-bold tracking-tight">
                  KL Sync
                </span>
              </Link>
              <button
                onClick={toggleCollapse}
                className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-muted-foreground hover:bg-surface-2"
                aria-label="Collapse sidebar"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
            </>
          )}
        </div>
        <nav className="custom-scrollbar flex-1 overflow-y-auto px-2 py-3">
          {!collapsed && (
            <p className="caption-label px-3 pb-1 text-muted-foreground">
              Workspace
            </p>
          )}
          {allNavItems.map((item) => renderNavLink(item, collapsed))}
        </nav>
        <div className="space-y-2 border-t p-3">
          {collapsed ? (
            <div className="flex justify-center">
              <ProfileAvatar user={user} size="sm" />
            </div>
          ) : (
            <div className="flex items-center gap-3 px-1">
              <ProfileAvatar user={user} />
              <div className="min-w-0">
                <p className="truncate text-sm font-bold">{user.name}</p>
                <p className="truncate font-mono text-[11px] text-muted-foreground">
                  {user.id}
                </p>
              </div>
            </div>
          )}
          <button
            onClick={handleSignOut}
            className={`flex min-h-[44px] w-full items-center gap-3 rounded-[--radius-md] text-sm font-semibold text-destructive hover:bg-error/10 ${collapsed ? 'justify-center' : 'px-3'}`}
            aria-label="Sign out"
          >
            <LogOut className="h-[18px] w-[18px]" />
            {!collapsed && <span>{t('logout', 'Sign out')}</span>}
          </button>
        </div>
      </aside>

      <nav
        className="apple-chrome-bottom fixed inset-x-0 bottom-0 z-40 lg:hidden"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        <div className="flex h-[var(--bottom-bar-height)] items-center justify-around">
          {bottomItems.map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? 'page' : undefined}
                onClick={() => triggerHaptic('selection')}
                className={`flex h-full flex-1 flex-col items-center justify-center gap-1 text-[10px] font-semibold ${active ? 'text-primary' : 'text-muted-foreground'}`}
              >
                <Icon className={`h-5 w-5 ${active ? 'scale-110' : ''}`} />
                <span>{item.label.split(' ')[0]}</span>
              </Link>
            );
          })}
          <button
            onClick={() => {
              triggerHaptic('light');
              setMoreOpen((current) => !current);
            }}
            aria-expanded={moreOpen}
            className={`flex h-full flex-1 flex-col items-center justify-center gap-1 text-[10px] font-semibold ${moreOpen || overflowItems.some((item) => isActive(item.href)) ? 'text-primary' : 'text-muted-foreground'}`}
          >
            <MoreHorizontal className="h-5 w-5" />
            <span>More</span>
          </button>
        </div>
        {moreOpen && (
          <>
            <div
              className="fixed inset-0 z-30"
              onClick={() => setMoreOpen(false)}
            />
            <div
              id="more-overflow-menu"
              className="apple-sheet animate-sheet-enter absolute bottom-full inset-x-0 z-40 p-4 max-h-[calc(100dvh-140px)] overflow-y-auto custom-scrollbar rounded-t-[28px] overflow-hidden border-t border-border shadow-2xl"
            >
              <div className="drag-handle" />
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                {overflowItems.map((item) => {
                  const active = isActive(item.href);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => {
                        triggerHaptic('selection');
                        setMoreOpen(false);
                      }}
                      className={`flex min-h-[72px] flex-col items-center justify-center gap-2 rounded-[--radius-lg] border p-2 text-center text-xs font-semibold transition-all duration-[--duration-fast] active:scale-95 ${active ? 'border-primary bg-primary/15 text-primary' : 'border-border bg-surface-2 text-muted-foreground hover:text-foreground hover:bg-surface-3'}`}
                    >
                      <Icon className="h-5 w-5" />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </nav>

      <main
        className={`flex h-full min-h-0 flex-col pt-[calc(var(--header-height)+env(safe-area-inset-top,0px))] pb-[calc(var(--bottom-bar-height)+env(safe-area-inset-bottom,0px))] transition-[padding] duration-[var(--duration-normal)] ${collapsed ? 'lg:ps-[var(--sidebar-collapsed)]' : 'lg:ps-[var(--sidebar-width)]'} lg:pt-0 lg:pb-0`}
      >
        <header className="apple-chrome hidden min-h-[var(--header-height)] items-center justify-between border-b px-6 lg:flex xl:px-8">
          <div className="flex items-center gap-3">
            {collapsed && (
              <button
                onClick={toggleCollapse}
                className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-muted-foreground hover:bg-surface-2"
                aria-label="Expand sidebar"
              >
                <Menu className="h-4 w-4" />
              </button>
            )}
            <div>
              <p className="caption-label text-muted-foreground">
                Student workspace
              </p>
              <h1 className="font-heading text-xl font-bold tracking-tight">
                {pageTitle}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              variant="info"
              className="hidden rounded-full px-3 py-1.5 sm:inline-flex"
            >
              <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-info" />
              Current semester
            </Badge>
            <LanguageSelector />
            <Link
              href="/dashboard/circulars"
              aria-label="Notifications"
              className="relative flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-muted-foreground hover:bg-surface-2 hover:text-foreground"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-success" />
            </Link>
            <div className="h-7 w-px bg-border" />
            <Link
              href="/dashboard/profile"
              className="flex min-h-[44px] items-center gap-2 rounded-full px-1.5 pr-3 hover:bg-surface-2"
            >
              <ProfileAvatar user={user} />
              <span className="hidden max-w-[160px] truncate text-sm font-semibold xl:block">
                {user.name}
              </span>
            </Link>
          </div>
        </header>
        <div
          id="main-content"
          tabIndex={-1}
          className="custom-scrollbar min-h-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-contain focus:outline-none"
        >
          <div className="mx-auto w-full max-w-[var(--content-max-width)] p-4 sm:p-5 lg:p-6">
            {children}
          </div>
        </div>
      </main>

      <AICopilot />
    </div>
  );
}
