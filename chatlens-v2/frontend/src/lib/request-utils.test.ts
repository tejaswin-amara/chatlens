import test from 'node:test';
import assert from 'node:assert/strict';
import { checkRateLimit } from './request-utils';

test('checkRateLimit allows requests up to limit and blocks excess', () => {
  const key = 'test-ip-123';
  const limit = 5;
  const windowMs = 10000;

  for (let i = 0; i < limit; i++) {
    const res = checkRateLimit(key, limit, windowMs);
    assert.strictEqual(res.allowed, true, `Request ${i + 1} should be allowed`);
    assert.strictEqual(res.remaining, limit - 1 - i);
  }

  const blockedRes = checkRateLimit(key, limit, windowMs);
  assert.strictEqual(
    blockedRes.allowed,
    false,
    'Request exceeding limit should be blocked'
  );
  assert.strictEqual(blockedRes.remaining, 0);
});
