import { validateChallenge } from 'capjs-core';
import { NextResponse } from 'next/server';
import { createHmac, randomBytes } from 'node:crypto';
import { consumeNonce, storeRedeemedToken, getCapSecret } from '@/lib/captcha';

export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const secret = getCapSecret();

    const result = await validateChallenge(secret, body, {
      scope: 'login',
      consumeNonce,
      signToken: ({ scope, expires, iat }) => {
        const payload = JSON.stringify({
          scope: scope ?? null,
          exp: expires,
          iat: iat || Date.now(),
          rnd: randomBytes(8).toString('hex'),
        });
        const b64 = Buffer.from(payload, 'utf8').toString('base64url');
        const sig = createHmac('sha256', secret)
          .update(b64)
          .digest('base64url');
        return `signed:${b64}.${sig}`;
      },
    });

    if (result.success && result.tokenKey) {
      await storeRedeemedToken(result.tokenKey, result.expires);
    }

    return NextResponse.json(result, {
      headers: {
        'Cache-Control': 'no-store, max-age=0',
      },
    });
  } catch (error) {
    console.error('Captcha redemption failed:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to redeem captcha token' },
      { status: 500 }
    );
  }
}
