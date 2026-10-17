'use client';

/* eslint-disable @next/next/no-img-element */

import { useEffect, useState } from 'react';
import {
  AlertCircle,
  Loader2,
  Lock,
  LogIn,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  User,
} from '@/components/ui/icons';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { triggerHaptic } from '@/lib/fluid-motion';
import { prefetchAllUserData } from '@/lib/data-prefetcher';
import { useI18n } from '@/lib/i18n';
import { LanguageSelector } from '@/components/ui/LanguageSelector';
import { Captcha } from '@/components/Captcha';

export default function LoginPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [captcha, setCaptcha] = useState('');
  const [captchaToken, setCaptchaToken] = useState('');
  const [captchaImage, setCaptchaImage] = useState<string | null>(null);
  const [captchaSessionId, setCaptchaSessionId] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [deviceId, setDeviceId] = useState('');
  const [loading, setLoading] = useState(false);
  const [captchaLoading, setCaptchaLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [autoSolveFailed, setAutoSolveFailed] = useState(false);

  const fetchCaptcha = async (preserveError = false): Promise<string> => {
    setCaptchaLoading(true);
    if (!preserveError) setError(null);
    try {
      const response = await fetch('/api/captcha', {
        signal: AbortSignal.timeout(12000),
      });
      const sid = response.headers.get('x-session-id');
      if (sid) setCaptchaSessionId(sid);
      const data = await response.json();
      if (
        !response.ok ||
        typeof data.captchaImage !== 'string' ||
        !data.captchaImage
      ) {
        throw new Error(data.error || 'Captcha service unavailable');
      }
      setCaptchaImage(data.captchaImage);
      setCaptchaToken('');
      if (
        typeof data.solvedCaptcha === 'string' &&
        data.solvedCaptcha.length > 0
      ) {
        setCaptcha(data.solvedCaptcha);
        setAutoSolveFailed(false);
      } else {
        setCaptcha('');
        setAutoSolveFailed(true);
      }
      return data.solvedCaptcha || '';
    } catch (err) {
      console.warn('[CAPTCHA] Bootstrap failed:', err);
      setCaptchaImage(null);
      setCaptcha('');
      setCaptchaToken('');
      setAutoSolveFailed(true);
      if (!preserveError)
        setError('Could not load the security code. Please retry.');
      return '';
    } finally {
      setCaptchaLoading(false);
    }
  };

  useEffect(() => {
    queueMicrotask(() => {
      try {
        void fetchCaptcha();
        const savedDevice = localStorage.getItem('kl_erp_device_id');
        if (savedDevice) setDeviceId(savedDevice);
      } catch {
        void fetchCaptcha();
      }
      const savedUser = localStorage.getItem('remember_username');
      if (savedUser) {
        setUsername(savedUser);
        setRememberMe(true);
      }
    });
  }, [router]);

  const handleLogin = async (
    event?: React.FormEvent,
    overrideCreds?: { u: string; p: string; c: string }
  ) => {
    event?.preventDefault();
    const u = overrideCreds ? overrideCreds.u : username;
    const p = overrideCreds ? overrideCreds.p : password;
    const c = overrideCreds ? overrideCreds.c : captcha;

    const cleanCaptcha = c
      .toLowerCase()
      .trim()
      .replace(/[^a-z]/g, '');
    if (!u || !p || !cleanCaptcha) {
      triggerHaptic('error');
      setError(
        'Please fill in all fields. The security code accepts lowercase letters a–z only.'
      );
      return;
    }
    setLoading(true);
    setError(null);
    setStatus(null);
    triggerHaptic('light');
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(captchaSessionId ? { 'x-session-id': captchaSessionId } : {}),
        },
        body: JSON.stringify({
          username: u.trim(),
          password: p,
          captcha: cleanCaptcha,
          captchaToken: captchaToken || undefined,
          sessionId: captchaSessionId || undefined,
          deviceId:
            deviceId ||
            (typeof localStorage !== 'undefined'
              ? localStorage.getItem('kl_erp_device_id')
              : '') ||
            '',
          rememberMe,
        }),
      });
      const data = await response.json();
      if (data.deviceId) {
        setDeviceId(data.deviceId);
        try {
          localStorage.setItem('kl_erp_device_id', data.deviceId);
        } catch {}
      }
      if (data.needsCaptchaRetry) {
        setError(null);
        setStatus(
          'First-time device setup — please enter the captcha once more.'
        );
        await fetchCaptcha(true);
        setLoading(false);
        triggerHaptic('warning');
        return;
      }
      if (!response.ok)
        throw new Error(data.message || data.error || 'Login failed');
      if (rememberMe) localStorage.setItem('remember_username', username);
      else localStorage.removeItem('remember_username');
      localStorage.removeItem('remember_password');
      try {
        localStorage.setItem(
          'kl_erp_academic_years',
          JSON.stringify(data.academicYears || [])
        );
        localStorage.setItem(
          'kl_erp_semesters',
          JSON.stringify(data.semesters || [])
        );
      } catch {}
      let academicYear = '';
      if (data.academicYears?.length) {
        academicYear = data.academicYears[0].value;
      }
      let semesterId = '';
      if (data.semesters?.length) {
        semesterId = data.semesters[0].value;
      }
      if (academicYear) localStorage.setItem('kl_erp_year', academicYear);
      if (semesterId) localStorage.setItem('kl_erp_sem', semesterId);
      if (username) localStorage.setItem('studentId', username);
      void prefetchAllUserData({ academicYear, semesterId });
      triggerHaptic('success');
      router.push('/dashboard');
    } catch (err: unknown) {
      triggerHaptic('error');
      setError(
        err instanceof Error && err.message
          ? err.message
          : 'An unexpected error occurred'
      );
      await fetchCaptcha(true);
    } finally {
      setLoading(false);
    }
  };

  const handleDemoMode = () => {
    triggerHaptic('selection');
    setUsername('2100030000');
    setPassword('demo_password');
    setCaptcha('demo');
    // ponytail: reuse handleLogin with overrides to bypass async state update delay
    void handleLogin(undefined, { u: '2100030000', p: 'demo_password', c: 'demo' });
  };

  return (
    <main className="relative flex h-[100dvh] w-full overflow-hidden bg-background text-foreground">
      <h1 className="sr-only">KL Sync Student Portal</h1>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_0%,rgba(79,70,200,0.10),transparent_35%),radial-gradient(circle_at_90%_100%,rgba(19,138,99,0.08),transparent_36%)]" />
      <div className="absolute right-4 top-4 z-30 flex items-center gap-2 sm:right-6 sm:top-6">
        <LanguageSelector />
      </div>



      <section className="relative flex min-h-[100dvh] flex-col overflow-y-auto py-6 sm:py-8 custom-scrollbar bg-background">
        <div className="m-auto w-full max-w-[420px] px-4 animate-spring-up">
          <Card variant="glass" className="rounded-[--radius-2xl] border-border/60 p-4 sm:p-6 shadow-xl backdrop-blur-xl">
            <CardHeader className="p-0 pb-4">
              <div className="mb-3 flex items-center gap-3">
                <div className="flex h-11 shrink-0 items-center justify-center rounded-xl border border-border/80 bg-surface-1 p-1.5 shadow-xs backdrop-blur-md">
                  <img
                    src="/logo.webp"
                    alt="KL University Logo"
                    className="h-full w-auto object-contain"
                  />
                </div>
                <div>
                  <h1 className="text-lg font-bold tracking-tight text-foreground leading-tight">
                    KL Sync
                  </h1>
                  <p className="text-[11px] text-muted-foreground font-medium">
                    KL University Student Portal
                  </p>
                </div>
              </div>

              <p className="caption-label mb-0.5 text-primary font-semibold">
                Welcome back
              </p>
              <h2 className="display-title text-2xl sm:text-3xl font-extrabold tracking-tight">
                Sign in to your{' '}
                <span className="text-gradient-brand">workspace.</span>
              </h2>
              <CardDescription className="mt-1 text-xs sm:text-sm">
                Use your student ERP credentials to continue.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {error && (
                <div
                  role="alert"
                  aria-live="assertive"
                  className="mb-3 flex items-start gap-2.5 rounded-[--radius-md] border border-error/35 bg-error/10 p-2.5 text-xs text-error sm:text-sm"
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p className="leading-relaxed">{error}</p>
                </div>
              )}
              {status && !error && (
                <div
                  role="status"
                  aria-live="polite"
                  className="mb-3 flex items-start gap-2.5 rounded-[--radius-md] border border-info/35 bg-info/10 p-2.5 text-xs text-info sm:text-sm"
                >
                  <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
                  <p className="leading-relaxed">{status}</p>
                </div>
              )}
              <form
                onSubmit={handleLogin}
                className="space-y-3"
                aria-label="Student ERP Authentication Form"
              >
                <div className="space-y-1">
                  <label
                    htmlFor="student-id-field"
                    className="caption-label text-muted-foreground"
                  >
                    {t('studentId', 'Student ID / username')}
                  </label>
                  <Input
                    id="student-id-field"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    placeholder="210003xxxx"
                    leftIcon={<User className="h-4 w-4" />}
                    aria-required="true"
                    autoComplete="username"
                  />
                </div>
                <div className="space-y-1">
                  <label
                    htmlFor="password-field"
                    className="caption-label text-muted-foreground"
                  >
                    {t('password', 'Password')}
                  </label>
                  <Input
                    id="password-field"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Enter your password"
                    leftIcon={<Lock className="h-4 w-4" />}
                    aria-required="true"
                    autoComplete="current-password"
                  />
                </div>
                <div className="space-y-1">
                  <div className="flex items-center justify-between gap-3">
                    <label
                      htmlFor="captcha-field"
                      className="caption-label text-muted-foreground"
                    >
                      {t('securityCode', 'Security code')}
                    </label>
                    <span className="text-[10px] font-semibold text-primary">
                      {autoSolveFailed
                        ? 'Type the code shown'
                        : 'Lowercase letters only'}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Input
                      id="captcha-field"
                      value={captcha}
                      onChange={(event) =>
                        setCaptcha(
                          event.target.value
                            .toLowerCase()
                            .replace(/[^a-z]/g, '')
                        )
                      }
                      placeholder="e.g. abcd"
                      aria-required="true"
                      autoCapitalize="none"
                      autoCorrect="off"
                      spellCheck={false}
                      className="min-w-0 flex-1 font-mono lowercase tracking-[0.25em]"
                    />
                    <div className="flex shrink-0 items-center gap-1.5">
                      <div className="flex h-11 w-[90px] items-center justify-center overflow-hidden rounded-[--radius-md] border border-border bg-surface-1 shadow-xs">
                        {captchaLoading ? (
                          <Loader2
                            className="h-4 w-4 animate-spin text-muted-foreground"
                            aria-label="Loading captcha"
                          />
                        ) : captchaImage ? (
                          <img
                            src={captchaImage}
                            alt="Security code"
                            className="h-full w-full object-contain mix-blend-normal"
                            onError={(event) => {
                              event.currentTarget.style.display = 'none';
                            }}
                          />
                        ) : null}
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        onClick={() => {
                          triggerHaptic('light');
                          setCaptchaToken('');
                          void fetchCaptcha();
                        }}
                        isLoading={captchaLoading}
                        disabled={captchaLoading}
                        aria-label="Refresh captcha"
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="remember-me-checkbox"
                    className="flex min-h-[44px] cursor-pointer items-center gap-2.5 text-xs sm:text-sm font-medium text-muted-foreground select-none hover:text-foreground transition-colors"
                  >
                    <input
                      id="remember-me-checkbox"
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(event) => setRememberMe(event.target.checked)}
                      className="h-4 w-4 rounded border-input bg-surface-2 text-primary accent-primary focus-visible:ring-2 focus-visible:ring-primary"
                    />
                    <span>{t('rememberMe', 'Remember me')}</span>
                  </label>
                </div>
                <Captcha onVerify={setCaptchaToken} />
                <Button
                  type="submit"
                  size="lg"
                  isLoading={loading}
                  disabled={loading || !captcha}
                  className="mt-1 w-full"
                >
                  <LogIn className="h-4 w-4" />
                  {t('signIn', 'Sign in')}
                </Button>

                <div className="relative flex items-center justify-center py-1">
                  <div className="flex-grow border-t border-border/60" />
                  <span className="shrink-0 px-3 text-[11px] font-medium text-muted-foreground">
                    or
                  </span>
                  <div className="flex-grow border-t border-border/60" />
                </div>

                <button
                  type="button"
                  onClick={handleDemoMode}
                  disabled={loading}
                  className="apple-pill flex min-h-[44px] w-full items-center justify-center gap-2 px-4 py-2.5 text-xs sm:text-sm font-semibold text-foreground hover:text-primary transition-all active:scale-[0.98] disabled:opacity-50"
                  aria-label="Explore Demo Portal"
                >
                  <Sparkles className="h-4 w-4 text-primary" />
                  <span>Explore Demo Portal</span>
                </button>
              </form>

              <div className="mt-3 flex items-center justify-center gap-1.5 text-[11px] text-muted-foreground">
                <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-success" />
                <span>Protected with AES-256 encrypted session tokens</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
      </main>
  );
}
