import test from 'node:test';
import assert from 'node:assert/strict';
import {
  encodeSession,
  decodeSession,
  ScraperSession,
  SessionDecodeError,
} from './session';

test('Challenger M1 Session - Valid Sessions Roundtrip', async () => {
  // 1. Standard session
  const standardSession: ScraperSession = {
    cookies: [
      { name: 'PHPSESSID', value: 'sess_1234567890' },
      { name: 'auth_token', value: 'tok_qwertyuiop' },
    ],
    csrfToken: 'csrf_token_val_999',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
  };

  const encodedStd = await encodeSession(standardSession);
  assert.ok(
    encodedStd.startsWith('enc.'),
    'Standard session encoding must start with enc.'
  );
  const decodedStd = await decodeSession(encodedStd);
  assert.deepEqual(decodedStd, standardSession);

  // 2. Minimal session (empty fields)
  const minimalSession: ScraperSession = {
    cookies: [],
    csrfToken: '',
  };
  const encodedMin = await encodeSession(minimalSession);
  const decodedMin = await decodeSession(encodedMin);
  assert.deepEqual(decodedMin, minimalSession);

  // 3. Complex Unicode & Special Characters
  const unicodeSession: ScraperSession = {
    cookies: [
      { name: 'user_lang', value: '中文_日本語_Русский_🚀_🔑' },
      { name: 'special_chars', value: '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~' },
    ],
    csrfToken: '🔒_secret_token_\n\r\t',
    userAgent: 'Adversarial Test Agent 🤖',
  };
  const encodedUni = await encodeSession(unicodeSession);
  const decodedUni = await decodeSession(encodedUni);
  assert.deepEqual(decodedUni, unicodeSession);

  // 4. Large Payload Session (100KB payload)
  const largeCookies = Array.from({ length: 500 }, (_, i) => ({
    name: `cookie_${i}`,
    value: `value_${i}_`.repeat(20),
  }));
  const largeSession: ScraperSession = {
    cookies: largeCookies,
    csrfToken: 'large_csrf_' + 'X'.repeat(5000),
    userAgent: 'Large User Agent ' + 'Y'.repeat(5000),
  };
  await assert.rejects(
    () => encodeSession(largeSession),
    /maximum allowed size/
  );
});

test('Challenger M1 Session - Invalid Tokens & Corrupted Payloads reject closed', async () => {
  // 1. Completely invalid base64 after enc.
  const invalidB64Enc = 'enc.!!!NotBase64!!!';
  await assert.rejects(() => decodeSession(invalidB64Enc), SessionDecodeError);

  // 2. Encrypted string too short (< 28 bytes raw)
  // 20 bytes of base64 -> 15 bytes raw (< 28 bytes minimum for IV + Tag)
  const shortEnc = 'enc.' + Buffer.from('short_bytes_12345').toString('base64');
  await assert.rejects(() => decodeSession(shortEnc), SessionDecodeError);

  // 3. Exactly 27 bytes payload (1 byte below threshold)
  const exact27 = 'enc.' + Buffer.from(new Uint8Array(27)).toString('base64');
  await assert.rejects(() => decodeSession(exact27), SessionDecodeError);

  // 4. Bit flipping / Tampering AES-GCM Ciphertext & Tag
  const validSession: ScraperSession = {
    cookies: [{ name: 'test', value: 'value' }],
    csrfToken: 'secret',
  };
  const validToken = await encodeSession(validSession);
  const rawBase64 = validToken.slice(4);
  const rawBuffer = Buffer.from(rawBase64, 'base64');

  // Flip bits in tag / ciphertext area
  rawBuffer[rawBuffer.length - 1] ^= 0xff;
  const tamperedToken = 'enc.' + rawBuffer.toString('base64');
  await assert.rejects(() => decodeSession(tamperedToken), SessionDecodeError);

  // 5. Corrupted b64. prefix payload
  const corruptedB64 = 'b64.{"invalid_json": ';
  await assert.rejects(() => decodeSession(corruptedB64), SessionDecodeError);

  // 6. Plain invalid string without enc. or b64. prefix
  const plainJunk = 'just_a_random_string_that_is_not_base64_or_json!';
  await assert.rejects(() => decodeSession(plainJunk), SessionDecodeError);
});

test('Challenger M1 Session - Null, Undefined, and Empty Inputs reject closed', async () => {
  await assert.rejects(() => decodeSession(null), SessionDecodeError);
  await assert.rejects(() => decodeSession(undefined), SessionDecodeError);
  await assert.rejects(() => decodeSession(''), SessionDecodeError);
  await assert.rejects(() => decodeSession('   '), SessionDecodeError);
});

test('Challenger M1 Session - Environment Secret Permutations & Key Mismatch', async () => {
  const originalEnvSecret = process.env.SESSION_SECRET;
  const originalNextAuthSecret = process.env.NEXTAUTH_SECRET;
  const originalVercelUrl = process.env.VERCEL_URL;

  try {
    // Scenario A: Custom SESSION_SECRET
    process.env.SESSION_SECRET = 'custom_secret_key_aaa_12345';
    delete process.env.NEXTAUTH_SECRET;
    delete process.env.VERCEL_URL;

    const sampleSession: ScraperSession = {
      cookies: [{ name: 'test_a', value: 'val_a' }],
      csrfToken: 'token_a',
    };
    const encodedSecretA = await encodeSession(sampleSession);
    const decodedSecretA = await decodeSession(encodedSecretA);
    assert.deepEqual(
      decodedSecretA,
      sampleSession,
      'Custom SESSION_SECRET encode/decode roundtrip'
    );

    // Scenario B: Key mismatch (decode with Secret B)
    process.env.SESSION_SECRET = 'completely_different_secret_bbb_67890';
    await assert.rejects(
      () => decodeSession(encodedSecretA),
      SessionDecodeError
    );

    // Scenario C: Fallback secret (no env vars set)
    delete process.env.SESSION_SECRET;
    delete process.env.NEXTAUTH_SECRET;
    delete process.env.VERCEL_URL;

    const fallbackEncoded = await encodeSession(sampleSession);
    const fallbackDecoded = await decodeSession(fallbackEncoded);
    assert.deepEqual(
      fallbackDecoded,
      sampleSession,
      'Encode/decode with default fallback secret key works'
    );
  } finally {
    // Restore original env state
    if (originalEnvSecret !== undefined)
      process.env.SESSION_SECRET = originalEnvSecret;
    else delete process.env.SESSION_SECRET;

    if (originalNextAuthSecret !== undefined)
      process.env.NEXTAUTH_SECRET = originalNextAuthSecret;
    else delete process.env.NEXTAUTH_SECRET;

    if (originalVercelUrl !== undefined)
      process.env.VERCEL_URL = originalVercelUrl;
    else delete process.env.VERCEL_URL;
  }
});

test('Challenger M1 Session - Node Legacy Cipher Format Fallback', async () => {
  // Synthesize legacy Node ciphertext structure: [IV 12][Tag 16][Ciphertext N]
  // In WebCrypto format, WebCrypto puts tag at end: [IV 12][Ciphertext N][Tag 16]
  // encodeSession creates standard WebCrypto layout.
  // Let's create a legacy layout token manually and test if decodeSession fallback catches it!

  const session: ScraperSession = {
    cookies: [{ name: 'legacy_node_cookie', value: 'node_val' }],
    csrfToken: 'legacy_node_csrf',
  };

  const standardToken = await encodeSession(session);
  const rawBase64 = standardToken.slice('enc.'.length);
  const rawBuffer = Buffer.from(rawBase64, 'base64');

  // Standard rawBuffer format: [IV 12][Ciphertext (byteLength - 28)][Tag 16]
  const iv = rawBuffer.subarray(0, 12);
  const ciphertext = rawBuffer.subarray(12, rawBuffer.length - 16);
  const tag = rawBuffer.subarray(rawBuffer.length - 16);

  // Rearrange into legacy Node layout: [IV 12][Tag 16][Ciphertext]
  const legacyBuffer = new Uint8Array(12 + 16 + ciphertext.byteLength);
  legacyBuffer.set(iv, 0);
  legacyBuffer.set(tag, 12);
  legacyBuffer.set(ciphertext, 28);

  const legacyToken = 'enc.' + Buffer.from(legacyBuffer).toString('base64');

  const decodedLegacyNode = await decodeSession(legacyToken);
  assert.deepEqual(
    decodedLegacyNode,
    session,
    'decodeSession legacy fallback must correctly decode [IV][Tag][Ciphertext] Node tokens'
  );
});
