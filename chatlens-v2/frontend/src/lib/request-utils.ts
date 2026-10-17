import { NextRequest } from 'next/server';

export function resolveSessionToken(request: NextRequest): string | undefined {
  const cookieValue = request.cookies.get('kl_erp_session')?.value;
  if (cookieValue) return cookieValue;

  const headerValue = request.headers.get('x-session-id');
  if (headerValue) return headerValue;

  const authHeader = request.headers
    .get('authorization')
    ?.replace(/^Bearer\s+/i, '');
  if (authHeader) return authHeader;

  return undefined;
}

export interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  resetMs: number;
}

const MAX_RATE_LIMIT_KEYS = 10_000;
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();

function pruneRateLimitMap(now: number): void {
  if (rateLimitMap.size < MAX_RATE_LIMIT_KEYS) return;
  for (const [key, value] of rateLimitMap) {
    if (value.resetAt <= now) rateLimitMap.delete(key);
    if (rateLimitMap.size < MAX_RATE_LIMIT_KEYS) break;
  }
}

export function checkRateLimit(
  key: string,
  limit: number = 60,
  windowMs: number = 60_000
): RateLimitResult {
  const now = Date.now();
  const safeLimit = Math.max(1, Math.floor(limit));
  const safeWindow = Math.max(1_000, Math.floor(windowMs));
  pruneRateLimitMap(now);

  const current = rateLimitMap.get(key);
  if (!current || current.resetAt <= now) {
    rateLimitMap.set(key, { count: 1, resetAt: now + safeWindow });
    return { allowed: true, remaining: safeLimit - 1, resetMs: safeWindow };
  }

  if (current.count >= safeLimit) {
    return {
      allowed: false,
      remaining: 0,
      resetMs: Math.max(0, current.resetAt - now),
    };
  }

  current.count += 1;
  return {
    allowed: true,
    remaining: safeLimit - current.count,
    resetMs: Math.max(0, current.resetAt - now),
  };
}

async function checkUpstashRateLimit(
  key: string,
  limit: number,
  windowMs: number
): Promise<RateLimitResult | null> {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) return null;

  const script = `
    local current = redis.call('INCR', KEYS[1])
    if current == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[1]) end
    local ttl = redis.call('PTTL', KEYS[1])
    return { current, ttl }
  `;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(['EVAL', script, '1', key, String(windowMs)]),
      signal: AbortSignal.timeout(1500),
    });
    if (!response.ok) return null;
    const payload = (await response.json()) as { result?: unknown };
    const result = Array.isArray(payload.result) ? payload.result : [];
    const count = Number(result[0]);
    const ttl = Number(result[1]);
    if (!Number.isFinite(count) || !Number.isFinite(ttl)) return null;
    return {
      allowed: count <= limit,
      remaining: Math.max(0, limit - count),
      resetMs: Math.max(1_000, ttl),
    };
  } catch (error) {
    console.warn('[RATE_LIMIT] Distributed limiter unavailable:', error);
    return null;
  }
}

export async function checkRateLimitDistributed(
  key: string,
  limit: number = 60,
  windowMs: number = 60_000
): Promise<RateLimitResult> {
  const distributed = await checkUpstashRateLimit(
    key,
    Math.max(1, Math.floor(limit)),
    Math.max(1_000, Math.floor(windowMs))
  );
  if (distributed) return distributed;
  return checkRateLimit(key, limit, windowMs);
}

export function getClientIP(request: NextRequest): string {
  // ponytail: auto-detect Vercel; upgrade to explicit allowlist if multi-provider needed
  const trustHeaders =
    process.env.TRUST_PROXY_HEADERS === 'true' ||
    process.env.VERCEL === '1';
  if (trustHeaders) {
    const xff = request.headers.get('x-forwarded-for');
    if (xff) return xff.split(',')[0].trim().slice(0, 128) || 'unknown';
    const realIp = request.headers.get('x-real-ip');
    if (realIp) return realIp.trim().slice(0, 128) || 'unknown';
  }

  return 'unknown';
}
