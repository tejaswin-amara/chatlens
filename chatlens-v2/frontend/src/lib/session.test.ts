import test from 'node:test';
import assert from 'node:assert/strict';
import {
  encodeSession,
  decodeSession,
  ScraperSession,
  SessionDecodeError,
} from './session';

test('encodeSession and decodeSession roundtrip with AES-256-GCM', async () => {
  const sampleSession: ScraperSession = {
    cookies: [
      { name: 'PHPSESSID', value: 'session_abc123' },
      { name: 'kl_token', value: 'token_xyz789' },
    ],
    csrfToken: 'csrf_test_secret_123',
    userAgent: 'Mozilla/5.0 Test Agent',
  };

  const encoded = await encodeSession(sampleSession);
  assert.ok(
    encoded.startsWith('enc.'),
    'Encoded session should start with enc.'
  );
  assert.deepEqual(await decodeSession(encoded), sampleSession);
});

test('decodeSession rejects legacy base64 sessions', async () => {
  const sampleSession: ScraperSession = {
    cookies: [{ name: 'PHPSESSID', value: 'legacy_sess' }],
    csrfToken: 'legacy_csrf',
  };
  const token =
    'b64.' + Buffer.from(JSON.stringify(sampleSession)).toString('base64');
  await assert.rejects(() => decodeSession(token), SessionDecodeError);
});

test('decodeSession rejects corrupted, short, and tampered payloads', async () => {
  await assert.rejects(
    () => decodeSession('enc.invalidbase64characters!!!'),
    SessionDecodeError
  );
  await assert.rejects(() => decodeSession('enc.aGVsbG8='), SessionDecodeError);

  const encoded = await encodeSession({
    cookies: [{ name: 'PHPSESSID', value: 'session_secret' }],
    csrfToken: 'csrf_secret',
  });
  const tampered = encoded.slice(0, -4) + 'AAAA';
  await assert.rejects(() => decodeSession(tampered), SessionDecodeError);
});

test('decodeSession rejects null, undefined, empty, and unprefixed inputs', async () => {
  await assert.rejects(() => decodeSession(null), SessionDecodeError);
  await assert.rejects(() => decodeSession(undefined), SessionDecodeError);
  await assert.rejects(() => decodeSession(''), SessionDecodeError);
  await assert.rejects(() => decodeSession('random-token'), SessionDecodeError);
});

test('isDemoSession identifies explicit fixture sessions without treating decode failures as demo', async () => {
  const { isDemoSession } = await import('./session');
  assert.strictEqual(isDemoSession(null), true);
  assert.strictEqual(
    isDemoSession({
      cookies: [{ name: 'PHPSESSID', value: 'demo_session' }],
      csrfToken: 'demo_csrf_token_123',
    }),
    true
  );
  assert.strictEqual(
    isDemoSession({
      cookies: [{ name: 'PHPSESSID', value: 'real_php_session_999' }],
      csrfToken: 'real_csrf_abc',
    }),
    false
  );
});

test('encodeSession throws in production when SESSION_SECRET is missing', async () => {
  const origNodeEnv = process.env.NODE_ENV;
  const origSecret = process.env.SESSION_SECRET;
  const origNextAuthSecret = process.env.NEXTAUTH_SECRET;
  try {
    delete process.env.SESSION_SECRET;
    delete process.env.NEXTAUTH_SECRET;
    (process.env as Record<string, string | undefined>).NODE_ENV = 'production';
    await assert.rejects(
      () =>
        encodeSession({
          cookies: [{ name: 'PHPSESSID', value: 'val' }],
          csrfToken: 'csrf',
        }),
      (err: Error) => err.message.includes('[SECURITY FATAL]')
    );
  } finally {
    (process.env as Record<string, string | undefined>).NODE_ENV = origNodeEnv;
    if (origSecret === undefined) delete process.env.SESSION_SECRET;
    else process.env.SESSION_SECRET = origSecret;
    if (origNextAuthSecret === undefined) delete process.env.NEXTAUTH_SECRET;
    else process.env.NEXTAUTH_SECRET = origNextAuthSecret;
  }
});
