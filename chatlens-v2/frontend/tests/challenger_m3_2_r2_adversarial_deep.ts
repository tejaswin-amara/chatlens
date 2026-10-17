import assert from 'node:assert/strict';
import { NextRequest } from 'next/server';
import { GET as fetchPhotoGET } from '../src/app/api/fetch-photo/route';
import { GET as erpProxyGET } from '../src/app/api/erp-proxy/[module]/route';
import {
  encodeSession,
  decodeSession,
  isDemoSession,
  ScraperSession,
} from '../src/lib/session';
import {
  checkRateLimit,
  getClientIP,
  resolveSessionToken,
} from '../src/lib/request-utils';

async function runAdversarialDeepVerification() {
  console.log('='.repeat(80));
  console.log(
    '🛡️ CHALLENGER 2: DEEP ADVERSARIAL STRESS & BOUNDARY VERIFICATION'
  );
  console.log('='.repeat(80));

  let passedTests = 0;
  let totalTests = 0;

  function record(name: string, fn: () => void | Promise<void>) {
    totalTests++;
    return async () => {
      try {
        await fn();
        passedTests++;
        console.log(`  ✓ [PASS] ${name}`);
      } catch (err) {
        console.error(`  ✖ [FAIL] ${name}`);
        console.error(`     Error:`, err);
        throw err;
      }
    };
  }

  // ---------------------------------------------------------------------------
  // 1. SSRF & Path Traversal Protections (/api/fetch-photo)
  // ---------------------------------------------------------------------------
  console.log('\n--- 1. SSRF & Path Traversal Defenses (/api/fetch-photo) ---');

  await record('fetch-photo rejects missing ID and path with 400', async () => {
    const req = new Request('http://localhost:3000/api/fetch-photo');
    const res = await fetchPhotoGET(req);
    assert.strictEqual(res.status, 400);
    const text = await res.text();
    assert.strictEqual(text, 'Missing ID or path');
  })();

  await record(
    'fetch-photo rejects non-alphanumeric ID (SSRF / SQLi / command inject)',
    async () => {
      const maliciousIds = [
        '2100030000; rm -rf /',
        '../../etc/passwd',
        'student_id<script>',
        '2100030000%00',
        'http://attacker.com/photo.jpg',
      ];
      for (const id of maliciousIds) {
        const req = new Request(
          `http://localhost:3000/api/fetch-photo?id=${encodeURIComponent(id)}`
        );
        const res = await fetchPhotoGET(req);
        assert.strictEqual(
          res.status,
          400,
          `Expected 400 for malicious ID: ${id}`
        );
        const text = await res.text();
        assert.strictEqual(text, 'Invalid ID format');
      }
    }
  )();

  await record(
    'fetch-photo rejects path traversal sequences (.. / %2e / :// / //)',
    async () => {
      const maliciousPaths = [
        '../sensitive/file.txt',
        'uploads/..%2f..%2fetc/passwd',
        '%2e%2e/uploads/photo.jpg',
        'http://169.254.169.254/latest/meta-data',
        '//internal-erp-server/api/secret',
      ];
      for (const p of maliciousPaths) {
        const req = new Request(
          `http://localhost:3000/api/fetch-photo?path=${encodeURIComponent(p)}`
        );
        const res = await fetchPhotoGET(req);
        assert.strictEqual(
          res.status,
          400,
          `Expected 400 for malicious path: ${p}`
        );
        const text = await res.text();
        assert.strictEqual(text, 'Invalid path');
      }
    }
  )();

  await record(
    'fetch-photo rejects paths outside of /uploads/ prefix',
    async () => {
      const nonUploadPaths = [
        '/api/admin/users',
        '/var/log/system.log',
        '/studentphotos/2100030000.jpg',
        '/config/database.json',
      ];
      for (const p of nonUploadPaths) {
        const validSession = await encodeSession({
          cookies: [{ name: 'PHPSESSID', value: 'real_session_123' }],
          csrfToken: 'real_csrf_456',
        });
        const reqReal = new Request(
          `http://localhost:3000/api/fetch-photo?path=${encodeURIComponent(p)}`,
          {
            headers: { 'x-session-id': validSession },
          }
        );
        const resReal = await fetchPhotoGET(reqReal);
        assert.strictEqual(
          resReal.status,
          400,
          `Expected 400 for non-uploads path: ${p}`
        );
        const text = await resReal.text();
        assert.strictEqual(text, 'Invalid photo path');
      }
    }
  )();

  await record(
    'fetch-photo returns demo placeholder SVG for demo session safely',
    async () => {
      const req = new Request(
        'http://localhost:3000/api/fetch-photo?id=2100030000',
        {
          headers: { 'x-session-id': 'demo_session' },
        }
      );
      const res = await fetchPhotoGET(req);
      assert.strictEqual(res.status, 200);
      assert.strictEqual(res.headers.get('Content-Type'), 'image/svg+xml');
      const text = await res.text();
      assert.ok(text.startsWith('<svg'));
    }
  )();

  // ---------------------------------------------------------------------------
  // 2. Session Integrity & Cryptographic Boundaries
  // ---------------------------------------------------------------------------
  console.log('\n--- 2. Session Integrity & Cryptographic Boundaries ---');

  await record(
    'AES-256-GCM encodeSession and decodeSession roundtrip',
    async () => {
      const sampleSession: ScraperSession = {
        cookies: [
          { name: 'PHPSESSID', value: 'secure_php_session_9999' },
          { name: 'KLU_AUTH', value: 'auth_hash_abc123' },
        ],
        csrfToken: 'secure_csrf_token_xyz888',
        userAgent: 'Mozilla/5.0 Challenger Agent',
      };

      const encoded = await encodeSession(sampleSession);
      assert.ok(
        encoded.startsWith('enc.'),
        'Encoded token must have enc. prefix'
      );

      const decoded = await decodeSession(encoded);
      assert.deepStrictEqual(decoded, sampleSession);
      assert.strictEqual(isDemoSession(decoded), false);
    }
  )();

  await record(
    'decodeSession handles bit-flipped / tampered ciphertext gracefully without crashing',
    async () => {
      const validToken = await encodeSession({
        cookies: [{ name: 'PHPSESSID', value: 'valid_val' }],
        csrfToken: 'valid_csrf',
      });

      const raw = Buffer.from(validToken.slice(4), 'base64');
      // Tamper with ciphertext byte
      raw[20] ^= 0xff;
      const tamperedToken = 'enc.' + raw.toString('base64');

      const decoded = await decodeSession(tamperedToken);
      // Should fallback to DEMO_SESSION without crashing
      assert.strictEqual(isDemoSession(decoded), true);
    }
  )();

  await record(
    'decodeSession handles truncated / short payload (<28 bytes)',
    async () => {
      const shortToken = 'enc.' + Buffer.from('short_bytes').toString('base64');
      const decoded = await decodeSession(shortToken);
      assert.strictEqual(isDemoSession(decoded), true);
    }
  )();

  await record(
    'decodeSession handles legacy b64. tokens seamlessly',
    async () => {
      const legacyPayload: ScraperSession = {
        cookies: [{ name: 'PHPSESSID', value: 'legacy_sess' }],
        csrfToken: 'legacy_csrf',
      };
      const legacyToken =
        'b64.' + Buffer.from(JSON.stringify(legacyPayload)).toString('base64');
      const decoded = await decodeSession(legacyToken);
      assert.deepStrictEqual(decoded, legacyPayload);
    }
  )();

  await record(
    'decodeSession handles null / undefined / empty string safely',
    async () => {
      assert.strictEqual(isDemoSession(await decodeSession(null)), true);
      assert.strictEqual(isDemoSession(await decodeSession(undefined)), true);
      assert.strictEqual(isDemoSession(await decodeSession('')), true);
    }
  )();

  // ---------------------------------------------------------------------------
  // 3. API Rate Limiting & Client IP Resolution
  // ---------------------------------------------------------------------------
  console.log('\n--- 3. API Rate Limiting & Client IP Resolution ---');

  await record(
    'checkRateLimit enforces sliding window threshold and returns remaining quota',
    () => {
      const key = `test-ip-${Date.now()}`;
      const r1 = checkRateLimit(key, 5, 1000);
      assert.strictEqual(r1.allowed, true);
      assert.strictEqual(r1.remaining, 4);

      checkRateLimit(key, 5, 1000);
      checkRateLimit(key, 5, 1000);
      checkRateLimit(key, 5, 1000);
      const r5 = checkRateLimit(key, 5, 1000);
      assert.strictEqual(r5.allowed, true);
      assert.strictEqual(r5.remaining, 0);

      const r6 = checkRateLimit(key, 5, 1000);
      assert.strictEqual(r6.allowed, false);
      assert.strictEqual(r6.remaining, 0);
    }
  )();

  await record(
    'getClientIP trusts forwarded headers only when explicitly configured',
    () => {
      const req1 = new NextRequest('http://localhost:3000/api/ai/chat', {
        headers: {
          'x-forwarded-for': '203.0.113.195, 70.41.3.18, 150.172.238.178',
        },
      });
      const originalTrust = process.env.TRUST_PROXY_HEADERS;
      delete process.env.TRUST_PROXY_HEADERS;
      assert.strictEqual(getClientIP(req1), 'unknown');
      process.env.TRUST_PROXY_HEADERS = 'true';
      assert.strictEqual(getClientIP(req1), '203.0.113.195');

      const req2 = new NextRequest('http://localhost:3000/api/ai/chat', {
        headers: { 'x-real-ip': '198.51.100.42' },
      });
      assert.strictEqual(getClientIP(req2), '198.51.100.42');

      const req3 = new NextRequest('http://localhost:3000/api/ai/chat');
      if (originalTrust === undefined) delete process.env.TRUST_PROXY_HEADERS;
      else process.env.TRUST_PROXY_HEADERS = originalTrust;
      assert.strictEqual(getClientIP(req3), 'unknown');
    }
  )();

  await record(
    'resolveSessionToken accepts only the auth cookie by default',
    () => {
      // Cookie priority over header and body
      const reqCookie = new NextRequest(
        'http://localhost:3000/api/erp-proxy/attendance',
        {
          headers: {
            cookie: 'kl_erp_session=cookie_val_123',
            'x-session-id': 'header_val_456',
          },
        }
      );
      assert.strictEqual(resolveSessionToken(reqCookie), 'cookie_val_123');

      // Header priority when no cookie
      const reqHeader = new NextRequest(
        'http://localhost:3000/api/erp-proxy/attendance',
        {
          headers: {
            'x-session-id': 'header_val_456',
          },
        }
      );
      assert.strictEqual(resolveSessionToken(reqHeader), undefined);

      const reqQuery = new NextRequest(
        'http://localhost:3000/api/erp-proxy/attendance?sessionId=query_val_999'
      );
      assert.strictEqual(resolveSessionToken(reqQuery), undefined);
    }
  )();

  // ---------------------------------------------------------------------------
  // 4. ERP Proxy Route Handler Boundaries (/api/erp-proxy/[module])
  // ---------------------------------------------------------------------------
  console.log('\n--- 4. ERP Proxy Route Handler Boundaries ---');

  await record('erp-proxy rejects unknown modules with 404', async () => {
    const req = new NextRequest(
      'http://localhost:3000/api/erp-proxy/nonexistent_module_xyz'
    );
    const res = await erpProxyGET(req, {
      params: Promise.resolve({ module: 'nonexistent_module_xyz' }),
    });
    assert.strictEqual(res.status, 404);
    const data = await res.json();
    assert.strictEqual(data.success, false);
    assert.ok(data.error.includes('Unknown module'));
  })();

  await record('erp-proxy rejects missing CSRF token with 400', async () => {
    const req = new NextRequest(
      'http://localhost:3000/api/erp-proxy/attendance'
    );
    const res = await erpProxyGET(req, {
      params: Promise.resolve({ module: 'attendance' }),
    });
    assert.strictEqual(res.status, 400);
    const data = await res.json();
    assert.strictEqual(data.success, false);
    assert.strictEqual(data.error, 'CSRF token missing');
  })();

  await record(
    'erp-proxy rejects missing academicYear/semesterId with 400 when CSRF is present',
    async () => {
      const req = new NextRequest(
        'http://localhost:3000/api/erp-proxy/attendance?csrfToken=test_csrf'
      );
      const res = await erpProxyGET(req, {
        params: Promise.resolve({ module: 'attendance' }),
      });
      assert.strictEqual(res.status, 400);
      const data = await res.json();
      assert.strictEqual(data.success, false);
      assert.strictEqual(data.error, 'Missing academicYear or semesterId');
    }
  )();

  await record(
    'erp-proxy serves demo attendance with parameter bindings correctly',
    async () => {
      const req = new NextRequest(
        'http://localhost:3000/api/erp-proxy/attendance?academicYear=2025-2026&semesterId=1&csrfToken=demo_csrf'
      );
      const res = await erpProxyGET(req, {
        params: Promise.resolve({ module: 'attendance' }),
      });
      assert.strictEqual(res.status, 200);
      const data = await res.json();
      assert.strictEqual(data.success, true);
      assert.ok(Array.isArray(data.attendanceData));
      assert.ok(data.attendanceData.length > 0);
      assert.strictEqual(data.attendanceData[0]['Academic Year'], '2025-2026');
      assert.strictEqual(data.attendanceData[0].Semester, '1');
    }
  )();

  await record(
    'erp-proxy serves demo timetable, marks, profile, fee, cgpa, circulars, hostels, library, exam-seating',
    async () => {
      const modules = [
        'timetable?academicYear=2025-2026&semesterId=1&csrfToken=demo_csrf',
        'marks?academicYear=2025-2026&semesterId=1&csrfToken=demo_csrf',
        'profile',
        'fee',
        'cgpa?academicYear=2025-2026&semesterId=1',
        'circulars',
        'hostels',
        'library',
        'exam-seating',
      ];

      for (const modQuery of modules) {
        const [mod, q] = modQuery.split('?');
        const url = `http://localhost:3000/api/erp-proxy/${mod}${q ? '?' + q : ''}`;
        const req = new NextRequest(url);
        const res = await erpProxyGET(req, {
          params: Promise.resolve({ module: mod }),
        });
        assert.strictEqual(
          res.status,
          200,
          `Module ${mod} failed with ${res.status}`
        );
        const data = await res.json();
        assert.strictEqual(
          data.success,
          true,
          `Module ${mod} returned success: false`
        );
      }
    }
  )();

  // ---------------------------------------------------------------------------
  // Summary
  // ---------------------------------------------------------------------------
  console.log('\n' + '='.repeat(80));
  console.log(
    `CHALLENGER 2 DEEP ADVERSARIAL SUMMARY: ${passedTests}/${totalTests} Tests Passed (100%)`
  );
  console.log('='.repeat(80) + '\n');
}

runAdversarialDeepVerification().catch((err) => {
  console.error('Fatal deep adversarial failure:', err);
  process.exit(1);
});
