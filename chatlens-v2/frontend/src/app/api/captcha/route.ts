import { NextRequest, NextResponse } from 'next/server';
import { getCaptcha } from '@/lib/scraper';
import { encodeSession, isDemoModeEnabled } from '@/lib/session';
import { DEMO_SESSION, DEMO_CAPTCHA_SVG } from '@/lib/fixtures';
import { checkRateLimitDistributed, getClientIP } from '@/lib/request-utils';

export const dynamic = 'force-dynamic';

const OCR_TIMEOUT_MS = 6000;
const KLU_CAPTCHA_MIN = 4;
const KLU_CAPTCHA_MAX = 7;
const CAPTCHA_COOKIE = 'kl_captcha_session';

/** Returns cleaned lowercase a-z string if it looks like a valid KLU captcha, else '' */
function validateCaptchaResult(raw: string): string {
  const cleaned = raw
    .trim()
    .toLowerCase()
    .replace(/[^a-z]/g, '');
  return cleaned.length >= KLU_CAPTCHA_MIN && cleaned.length <= KLU_CAPTCHA_MAX
    ? cleaned
    : '';
}

async function runOcrEngine(
  base64: string,
  engine: string,
  apiKey: string,
  signal: AbortSignal
): Promise<string> {
  const formData = new URLSearchParams();
  formData.append('base64Image', `data:image/png;base64,${base64}`);
  formData.append('OCREngine', engine);

  const res = await fetch('https://api.ocr.space/parse/image', {
    method: 'POST',
    headers: {
      apikey: apiKey,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
    signal,
  });

  if (!res.ok) return '';
  const ocrData = await res.json();
  const rawText = ocrData?.ParsedResults?.[0]?.ParsedText || '';
  console.log(`[OCR Engine ${engine}] Raw text:`, rawText);
  return validateCaptchaResult(rawText);
}

async function solveCaptchaImage(
  base64: string,
  apiKey: string
): Promise<string> {
  const controller2 = new AbortController();
  const timer2 = setTimeout(() => controller2.abort(), OCR_TIMEOUT_MS);
  const controller1 = new AbortController();
  const timer1 = setTimeout(() => controller1.abort(), OCR_TIMEOUT_MS);

  try {
    const results = await Promise.allSettled([
      runOcrEngine(base64, '2', apiKey, controller2.signal),
      runOcrEngine(base64, '1', apiKey, controller1.signal),
    ]);
    for (const result of results) {
      if (result.status === 'fulfilled' && result.value) return result.value;
    }
  } finally {
    clearTimeout(timer2);
    clearTimeout(timer1);
  }
  return '';
}

function withCaptchaCookie(
  response: NextResponse,
  sessionId: string
): NextResponse {
  response.headers.set('x-session-id', sessionId);
  response.headers.set('Access-Control-Expose-Headers', 'x-session-id');
  response.cookies.set(CAPTCHA_COOKIE, sessionId, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 5 * 60,
  });
  return response;
}

export async function GET(request?: NextRequest) {
  const effectiveRequest =
    request ?? new NextRequest('http://localhost/api/captcha');
  const limit = await checkRateLimitDistributed(
    `captcha:ip:${getClientIP(effectiveRequest)}`,
    30,
    60_000
  );
  if (!limit.allowed) {
    return NextResponse.json(
      {
        success: false,
        error: 'Too many captcha requests. Please try again later.',
      },
      {
        status: 429,
        headers: {
          'Cache-Control': 'no-store, max-age=0',
          'Retry-After': String(Math.ceil(limit.resetMs / 1000)),
        },
      }
    );
  }

  try {
    const demoMode = isDemoModeEnabled();
    const apiKey = process.env.OCR_SPACE_API_KEY || 'helloworld';
    let captchaImage = '';
    let session;
    let solvedCaptcha = '';

    if (demoMode) {
      captchaImage = DEMO_CAPTCHA_SVG;
      session = DEMO_SESSION;
      solvedCaptcha = 'abcd';
    } else {
      try {
        const captchaRes = await getCaptcha({
          signal: AbortSignal.timeout(8000),
        });
        captchaImage = captchaRes.captchaImage;
        session = captchaRes.session;
      } catch (error) {
        console.error('[CAPTCHA] ERP unreachable:', error);
        return NextResponse.json(
          {
            success: false,
            error: 'Captcha service is temporarily unavailable.',
          },
          { status: 503 }
        );
      }
    }

    if (demoMode && session.csrfToken.includes('demo_csrf_token_123')) {
      solvedCaptcha = 'abcd';
    } else if (apiKey && !solvedCaptcha) {
      const cleanBase64 = captchaImage
        .replace(/^data:image\/[a-z]+;base64,/, '')
        .replace(/[\r\n\s]/g, '');
      solvedCaptcha = await solveCaptchaImage(cleanBase64, apiKey);
    }

    const sessionId = await encodeSession(session);
    return withCaptchaCookie(
      NextResponse.json(
        { captchaImage, solvedCaptcha, rule: 'lowercase_letters_only' },
        { headers: { 'Cache-Control': 'no-store, max-age=0' } }
      ),
      sessionId
    );
  } catch (error) {
    console.error('[CAPTCHA] Unexpected error:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch captcha.' },
      { status: 503 }
    );
  }
}
