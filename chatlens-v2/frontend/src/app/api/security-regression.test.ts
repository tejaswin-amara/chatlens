import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { NextRequest } from 'next/server';
import { GET as getErpProxy } from './erp-proxy/[module]/route';
import { verifyCaptchaToken } from '@/lib/captcha';
import robots from '@/app/robots';

const env = process.env as Record<string, string | undefined>;
const originalDemoMode = env.KL_SYNC_DEMO_MODE;
const originalNodeEnv = env.NODE_ENV;

test('production CAPTCHA verification rejects demo and structural legacy tokens', async () => {
  env.KL_SYNC_DEMO_MODE = 'false';
  env.NODE_ENV = 'production';
  try {
    assert.strictEqual(await verifyCaptchaToken('demo_token'), false);
    assert.strictEqual(await verifyCaptchaToken('demo_csrf_token_123'), false);
    assert.strictEqual(
      await verifyCaptchaToken('aabbccdd:0011223344556677'),
      false
    );
  } finally {
    if (originalDemoMode === undefined) delete env.KL_SYNC_DEMO_MODE;
    else env.KL_SYNC_DEMO_MODE = originalDemoMode;
    if (originalNodeEnv === undefined) delete env.NODE_ENV;
    else env.NODE_ENV = originalNodeEnv;
  }
});

test('ERP proxy unauthenticated response is explicitly private and non-cacheable', async () => {
  const previousDemoMode = env.KL_SYNC_DEMO_MODE;
  env.KL_SYNC_DEMO_MODE = 'false';
  try {
    const response = await getErpProxy(
      new NextRequest(
        'http://localhost/api/erp-proxy/attendance?academicYear=2025-2026&semesterId=1'
      ),
      { params: Promise.resolve({ module: 'attendance' }) }
    );
    assert.strictEqual(response.status, 401);
    assert.match(response.headers.get('cache-control') || '', /private/);
    assert.match(response.headers.get('cache-control') || '', /no-store/);
    assert.strictEqual(response.headers.get('vary'), 'Cookie');
  } finally {
    if (previousDemoMode === undefined) delete env.KL_SYNC_DEMO_MODE;
    else env.KL_SYNC_DEMO_MODE = previousDemoMode;
  }
});

test('service worker never caches API requests and pre-cache list has no missing icons', () => {
  const source = readFileSync('public/sw.js', 'utf8');
  assert.match(source, /url\.pathname\.startsWith\('\/api\/'\)/);
  assert.doesNotMatch(source, /cache\.put\(request[\s\S]{0,120}\/api\//);
  assert.match(source, /icon-192\.png/);
  assert.match(source, /icon-512\.png/);
});

test('robots metadata is explicit and excludes protected application paths', () => {
  const result = robots();
  assert.deepEqual(result.rules, {
    userAgent: '*',
    allow: '/',
    disallow: ['/api/', '/dashboard/'],
  });
  assert.match(String(result.sitemap), /klhb\.vercel\.app\/sitemap\.xml/);
});
