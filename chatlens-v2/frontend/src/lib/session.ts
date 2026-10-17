import type { ScraperSession } from './scraper';

export type { ScraperSession };

const ENC_PREFIX = 'enc.';
const MAX_SESSION_BYTES = 64 * 1024;

let devSessionSecret: string | null = null;

function getSecret(): string {
  if (process.env.SESSION_SECRET) return process.env.SESSION_SECRET;
  if (process.env.NEXTAUTH_SECRET) return process.env.NEXTAUTH_SECRET;

  if (process.env.NODE_ENV === 'production') {
    throw new Error(
      '[SECURITY FATAL] SESSION_SECRET environment variable is missing in production!'
    );
  }

  if (!devSessionSecret) {
    devSessionSecret =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2) +
          Math.random().toString(36).slice(2);
    console.warn(
      '[KL-SYNC DEV] Using ephemeral SESSION_SECRET. Sessions will reset on server restart. Set SESSION_SECRET in .env.local to persist.'
    );
  }
  return devSessionSecret;
}

export class SessionDecodeError extends Error {
  constructor(message = 'Invalid or expired session') {
    super(message);
    this.name = 'SessionDecodeError';
  }
}

export function isDemoModeEnabled(): boolean {
  return process.env.KL_SYNC_DEMO_MODE === 'true';
}

export function isDemoSession(
  session: ScraperSession | null | undefined
): boolean {
  if (!session) return true;
  if (!session.csrfToken || session.csrfToken.includes('demo')) return true;
  if (!session.cookies || session.cookies.length === 0) return true;
  return session.cookies.some((cookie) => cookie.value?.includes('demo'));
}

function validateSessionShape(value: unknown): ScraperSession {
  if (!value || typeof value !== 'object') {
    throw new SessionDecodeError();
  }

  const candidate = value as Partial<ScraperSession>;
  if (
    !Array.isArray(candidate.cookies) ||
    typeof candidate.csrfToken !== 'string'
  ) {
    throw new SessionDecodeError();
  }

  const cookies = candidate.cookies.map((cookie) => {
    if (!cookie || typeof cookie !== 'object') throw new SessionDecodeError();
    const item = cookie as { name?: unknown; value?: unknown };
    if (typeof item.name !== 'string' || typeof item.value !== 'string')
      throw new SessionDecodeError();
    return { name: item.name, value: item.value };
  });

  return {
    cookies,
    csrfToken: candidate.csrfToken,
    ...(typeof candidate.userAgent === 'string'
      ? { userAgent: candidate.userAgent }
      : {}),
  };
}

async function getCryptoKey(): Promise<CryptoKey> {
  const secretBytes = new TextEncoder().encode(getSecret());
  const hash = await crypto.subtle.digest('SHA-256', secretBytes);
  return crypto.subtle.importKey('raw', hash, { name: 'AES-GCM' }, false, [
    'encrypt',
    'decrypt',
  ]);
}

export async function encodeSession(session: ScraperSession): Promise<string> {
  const validated = validateSessionShape(session);
  const json = JSON.stringify(validated);
  const data = new TextEncoder().encode(json);
  if (data.byteLength > MAX_SESSION_BYTES) {
    throw new Error('Session payload exceeds the maximum allowed size');
  }

  const key = await getCryptoKey();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encryptedBuffer = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    key,
    data
  );

  const combined = new Uint8Array(iv.byteLength + encryptedBuffer.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(encryptedBuffer), iv.byteLength);

  return ENC_PREFIX + Buffer.from(combined).toString('base64url');
}

export async function decodeSession(
  token: string | null | undefined
): Promise<ScraperSession> {
  if (!token || !token.startsWith(ENC_PREFIX)) {
    throw new SessionDecodeError();
  }

  if (
    isDemoModeEnabled() &&
    (token.includes('demo') || token === 'enc.demo_session_data')
  ) {
    return {
      cookies: [
        { name: 'PHPSESSID', value: 'sess_demo_123456' },
        { name: 'kl_device', value: 'device_demo_123456' },
      ],
      csrfToken: 'demo_csrf_token_123',
      userAgent: 'Mozilla/5.0 Demo Browser',
    };
  }

  try {
    const raw = Buffer.from(token.slice(ENC_PREFIX.length), 'base64url');
    if (raw.length < 28 || raw.length > MAX_SESSION_BYTES + 28) {
      throw new SessionDecodeError();
    }

    const iv = raw.subarray(0, 12);
    const ciphertextWithTag = raw.subarray(12);
    const key = await getCryptoKey();

    let decryptedBuffer: ArrayBuffer;
    try {
      decryptedBuffer = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv },
        key,
        ciphertextWithTag
      );
    } catch {
      // Decode legacy Node layout only for encrypted tokens already issued by this app.
      const tag = raw.subarray(12, 28);
      const ciphertext = raw.subarray(28);
      const rearranged = new Uint8Array(ciphertext.byteLength + tag.byteLength);
      rearranged.set(ciphertext, 0);
      rearranged.set(tag, ciphertext.byteLength);
      decryptedBuffer = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv },
        key,
        rearranged
      );
    }

    const decoded = JSON.parse(new TextDecoder().decode(decryptedBuffer));
    return validateSessionShape(decoded);
  } catch (error) {
    if (error instanceof SessionDecodeError) throw error;
    throw new SessionDecodeError();
  }
}
