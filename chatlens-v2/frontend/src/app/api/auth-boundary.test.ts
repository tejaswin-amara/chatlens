import test from 'node:test';
import assert from 'node:assert/strict';
import { NextRequest } from 'next/server';
import { GET as handleErpProxy } from '@/app/api/erp-proxy/[module]/route';
import { POST as handleAiChat } from '@/app/api/ai/chat/route';
import { GET as handlePhoto } from '@/app/api/fetch-photo/route';

function withoutDemoMode<T>(callback: () => Promise<T>): Promise<T> {
  const previous = process.env.KL_SYNC_DEMO_MODE;
  delete process.env.KL_SYNC_DEMO_MODE;
  return callback().finally(() => {
    if (previous === undefined) delete process.env.KL_SYNC_DEMO_MODE;
    else process.env.KL_SYNC_DEMO_MODE = previous;
  });
}

test('protected ERP, AI, and photo routes reject missing sessions', async () => {
  await withoutDemoMode(async () => {
    const erpResponse = await handleErpProxy(
      new NextRequest('http://localhost/api/erp-proxy/profile'),
      { params: Promise.resolve({ module: 'profile' }) }
    );
    assert.equal(erpResponse.status, 401);

    const aiResponse = await handleAiChat(
      new NextRequest('http://localhost/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: 'Show my attendance' }],
        }),
      })
    );
    assert.equal(aiResponse.status, 401);

    const photoResponse = await handlePhoto(
      new Request('http://localhost/api/fetch-photo?id=2100030000')
    );
    assert.equal(photoResponse.status, 401);
  });
});

test('protected ERP routes reject malformed session cookies', async () => {
  await withoutDemoMode(async () => {
    const response = await handleErpProxy(
      new NextRequest('http://localhost/api/erp-proxy/profile', {
        headers: { cookie: 'kl_erp_session=enc.corrupted' },
      }),
      { params: Promise.resolve({ module: 'profile' }) }
    );
    assert.equal(response.status, 401);
  });
});
