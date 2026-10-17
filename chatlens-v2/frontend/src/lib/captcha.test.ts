import test from 'node:test';
import assert from 'node:assert';
import crypto from 'node:crypto';
import {
  verifyCaptchaToken,
  storeRedeemedToken,
  consumeNonce,
  getCapSecret,
} from './captcha';

test('getCapSecret always returns a valid secret of at least 16 bytes', () => {
  const secret = getCapSecret();
  assert.ok(secret);
  assert.ok(typeof secret === 'string');
  assert.ok(secret.length >= 16);
});

test('verifyCaptchaToken rejects missing or invalid tokens', async () => {
  assert.strictEqual(await verifyCaptchaToken(null), false);
  assert.strictEqual(await verifyCaptchaToken(undefined), false);
  assert.strictEqual(await verifyCaptchaToken(''), false);
  assert.strictEqual(
    await verifyCaptchaToken('invalid-token-without-colon'),
    false
  );
});

test('verifyCaptchaToken validates signed stateless HMAC tokens and prevents replays', async () => {
  const secret = getCapSecret();
  const payload = JSON.stringify({
    scope: 'login',
    exp: Date.now() + 60000,
    iat: Date.now(),
    rnd: crypto.randomBytes(8).toString('hex'),
  });
  const b64 = Buffer.from(payload, 'utf8').toString('base64url');
  const sig = crypto
    .createHmac('sha256', secret)
    .update(b64)
    .digest('base64url');
  const signedToken = `signed:${b64}.${sig}`;

  // First verification should pass
  assert.strictEqual(await verifyCaptchaToken(signedToken), true);

  // Second verification of same token should fail (burned/replay prevented)
  assert.strictEqual(await verifyCaptchaToken(signedToken), false);

  // Tampered signature should fail
  const tampered = `signed:${b64}.tamperedSig123`;
  assert.strictEqual(await verifyCaptchaToken(tampered), false);

  // Expired signed token should fail
  const expiredPayload = JSON.stringify({
    scope: 'login',
    exp: Date.now() - 1000,
    iat: Date.now() - 10000,
    rnd: crypto.randomBytes(8).toString('hex'),
  });
  const expiredB64 = Buffer.from(expiredPayload, 'utf8').toString('base64url');
  const expiredSig = crypto
    .createHmac('sha256', secret)
    .update(expiredB64)
    .digest('base64url');
  assert.strictEqual(
    await verifyCaptchaToken(`signed:${expiredB64}.${expiredSig}`),
    false
  );
});

test('storeRedeemedToken and verifyCaptchaToken lifecycle (single-use token burn)', async () => {
  const challengeId = 'test-challenge-' + Date.now();
  const verToken = 'verification-secret-xyz';

  // Derive expected tokenKey matching verifyCaptchaToken internal logic:
  // sha256Hex(verToken)
  const hash = crypto
    .createHash('sha256')
    .update(verToken, 'utf-8')
    .digest('hex');
  const tokenKey = `${challengeId}:${hash}`;

  const expiresAt = Date.now() + 60000; // 1 min in future
  await storeRedeemedToken(tokenKey, expiresAt);

  const fullToken = `${challengeId}:${verToken}`;

  // First verification must succeed
  const firstCheck = await verifyCaptchaToken(fullToken);
  assert.strictEqual(firstCheck, true);

  // Second verification must fail (token burned on first check)
  const secondCheck = await verifyCaptchaToken(fullToken);
  assert.strictEqual(secondCheck, false);
});

test('consumeNonce enforces single-use nonces', async () => {
  const sigHex = 'nonce-sig-' + Math.random().toString(36).slice(2);
  const ttl = 10000;

  const firstConsume = await consumeNonce(sigHex, ttl);
  assert.strictEqual(firstConsume, true);

  // Replay attempt must return false
  const replayConsume = await consumeNonce(sigHex, ttl);
  assert.strictEqual(replayConsume, false);
});
