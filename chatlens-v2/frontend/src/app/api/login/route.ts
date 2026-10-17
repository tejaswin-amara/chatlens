import { NextRequest, NextResponse } from 'next/server';
import { loginAndFetchSemesters, ScraperSession } from '@/lib/scraper';
import { decodeSession, encodeSession, isDemoModeEnabled } from '@/lib/session';
import { verifyCaptchaToken } from '@/lib/captcha';
import { DEMO_LOGIN_RESULT, DEMO_SESSION } from '@/lib/fixtures';
import { checkRateLimitDistributed, getClientIP } from '@/lib/request-utils';

export const dynamic = 'force-dynamic';

const CAPTCHA_COOKIE = 'kl_captcha_session';
const SESSION_COOKIE = 'kl_erp_session';

function setCookie(
  response: NextResponse,
  name: string,
  value: string,
  maxAge: number
): NextResponse {
  response.cookies.set(name, value, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge,
  });
  return response;
}

function clearCookie(response: NextResponse, name: string): NextResponse {
  response.cookies.set(name, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  });
  return response;
}

function safeLoginError(error: unknown): {
  message: string;
  status: number;
  isOffline?: boolean;
} {
  const message = error instanceof Error ? error.message : '';
  if (
    message.includes('fetch failed') ||
    message.includes('ENOTFOUND') ||
    message.includes('ETIMEDOUT') ||
    message.includes('ECONNREFUSED') ||
    message.includes('KLU ERP server error') ||
    message.includes('ERP login page structure')
  ) {
    return {
      message:
        'KL ERP server is currently unreachable. Please try again later.',
      status: 502,
      isOffline: true,
    };
  }
  return {
    message: 'Login failed. Please verify your credentials and try again.',
    status: 401,
  };
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const username =
      typeof body.username === 'string' ? body.username.trim() : '';
    const password = typeof body.password === 'string' ? body.password : '';
    const captcha =
      typeof body.captcha === 'string' ? body.captcha.trim().toLowerCase() : '';
    const captchaToken =
      typeof body.captchaToken === 'string' ? body.captchaToken : '';
    const deviceId = typeof body.deviceId === 'string' ? body.deviceId : '';
    const rememberMe = body.rememberMe === true;

    if (!username || !password || !captcha) {
      return NextResponse.json(
        { success: false, message: 'Missing required fields' },
        { status: 400 }
      );
    }

    const clientIp = getClientIP(request);
    const accountKey = username.toLowerCase().slice(0, 128);
    const ipLimit = await checkRateLimitDistributed(
      `login:ip:${clientIp}`,
      10,
      10 * 60 * 1000
    );
    const accountLimit = await checkRateLimitDistributed(
      `login:account:${accountKey}`,
      8,
      10 * 60 * 1000
    );
    if (!ipLimit.allowed || !accountLimit.allowed) {
      const retryAfter = Math.ceil(
        Math.max(ipLimit.resetMs, accountLimit.resetMs) / 1000
      );
      return NextResponse.json(
        {
          success: false,
          message: 'Too many login attempts. Please try again later.',
        },
        {
          status: 429,
          headers: {
            'Cache-Control': 'no-store, max-age=0',
            'Retry-After': String(retryAfter),
          },
        }
      );
    }

    const demoMode = isDemoModeEnabled();
    const isExplicitDemoUser =
      demoMode &&
      (username === 'demo' ||
        username === 'teststudent' ||
        username === '2100030000');
    if (
      !isExplicitDemoUser &&
      !(await verifyCaptchaToken(captchaToken))
    ) {
      return NextResponse.json(
        {
          success: false,
          message: 'Captcha verification failed. Please try again.',
        },
        { status: 400 }
      );
    }

    const captchaSessionId =
      request.cookies.get(CAPTCHA_COOKIE)?.value ||
      request.headers.get('x-session-id') ||
      request.headers.get('authorization')?.replace(/^Bearer\s+/i, '') ||
      (typeof body.sessionId === 'string' ? body.sessionId : undefined);

    if (!captchaSessionId) {
      return NextResponse.json(
        { success: false, message: 'Session expired. Please refresh captcha.' },
        { status: 400 }
      );
    }

    let session: ScraperSession;
    try {
      session = await decodeSession(captchaSessionId);
    } catch {
      if (
        demoMode &&
        (isExplicitDemoUser || captchaSessionId.includes('demo'))
      ) {
        session = DEMO_SESSION;
      } else {
        return NextResponse.json(
          {
            success: false,
            message: 'Captcha session is invalid. Please refresh the captcha.',
          },
          { status: 400 }
        );
      }
    }

    let result;
    try {
      if (
        isExplicitDemoUser ||
        session.csrfToken.includes('demo_csrf') ||
        session.csrfToken.includes('csrf_test_live')
      ) {
        if (!demoMode) throw new Error('Invalid login request');
        result = {
          ...DEMO_LOGIN_RESULT,
          deviceId: deviceId || DEMO_LOGIN_RESULT.deviceId,
        };
      } else {
        result = await loginAndFetchSemesters(
          username,
          password,
          captcha,
          session,
          deviceId
        );
      }
    } catch (error) {
      const safe = safeLoginError(error);
      return NextResponse.json(
        {
          success: false,
          message: safe.message,
          ...(safe.isOffline ? { isOffline: true } : {}),
        },
        { status: safe.status }
      );
    }

    const updatedSessionId = await encodeSession(result.session);
    if (result.needsCaptchaRetry) {
      const response = NextResponse.json({
        success: false,
        needsCaptchaRetry: true,
        message: result.message,
        sessionId: updatedSessionId,
      });
      response.headers.set('x-session-id', updatedSessionId);
      return setCookie(
        clearCookie(response, SESSION_COOKIE),
        CAPTCHA_COOKIE,
        updatedSessionId,
        5 * 60
      );
    }

    const response = NextResponse.json({
      success: true,
      message: 'Login successful',
      sessionId: updatedSessionId,
      deviceId: result.deviceId,
      academicYears: result.academicYears,
      semesters: result.semesters,
    });
    response.headers.set('x-session-id', updatedSessionId);
    clearCookie(response, CAPTCHA_COOKIE);
    return setCookie(
      response,
      SESSION_COOKIE,
      updatedSessionId,
      rememberMe ? 60 * 60 * 24 * 30 : 60 * 60 * 24
    );
  } catch (error) {
    console.error(
      '[AUTH_ERROR]',
      error instanceof Error ? error.message : 'Unknown login error'
    );
    return NextResponse.json(
      { success: false, message: 'Login failed. Please try again.' },
      { status: 400 }
    );
  }
}
