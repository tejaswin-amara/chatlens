import test from 'node:test';
import assert from 'node:assert/strict';
import { fetchProfileData } from './profile';
import { ScraperSession } from './http-jar';

test('fetchProfileData limits sub-tab request concurrency to maximum 3 simultaneous requests', async () => {
  const originalFetch = globalThis.fetch;

  let activeRequests = 0;
  let maxConcurrentSeen = 0;
  let totalSubTabRequests = 0;

  // HTML fixture containing 9 sub-tab URLs to trigger sub-tab batch fetching
  const mockMainProfileHtml = `
    <html>
      <body>
        <div class="profile_bg">
          <h4>John Doe Student</h4>
        </div>
        <p>University ID: 2100030099</p>
        <ul class="nav">
          <li><a href="/index.php?r=tab1">Tab One</a></li>
          <li><a href="/index.php?r=tab2">Tab Two</a></li>
          <li><a href="/index.php?r=tab3">Tab Three</a></li>
          <li><a href="/index.php?r=tab4">Tab Four</a></li>
          <li><a href="/index.php?r=tab5">Tab Five</a></li>
          <li><a href="/index.php?r=tab6">Tab Six</a></li>
          <li><a href="/index.php?r=tab7">Tab Seven</a></li>
          <li><a href="/index.php?r=tab8">Tab Eight</a></li>
          <li><a href="/index.php?r=tab9">Tab Nine</a></li>
        </ul>
      </body>
    </html>
  `;

  try {
    globalThis.fetch = async (input: RequestInfo | URL) => {
      const urlStr = input.toString();

      // Main profile fetch
      if (
        urlStr.includes('/StudentProfile/viewprofile') ||
        urlStr.includes('viewprofile')
      ) {
        return new Response(mockMainProfileHtml, { status: 200 });
      }

      // Sub-tab fetches
      if (urlStr.includes('/index.php?r=tab')) {
        activeRequests++;
        totalSubTabRequests++;
        if (activeRequests > maxConcurrentSeen) {
          maxConcurrentSeen = activeRequests;
        }

        // Add a slight artificial delay (20ms) to ensure concurrent requests overlap
        await new Promise((resolve) => setTimeout(resolve, 20));

        activeRequests--;
        return new Response(
          `<table><tr><th>Field</th><th>Value</th></tr><tr><td>Data</td><td>Val</td></tr></table>`,
          {
            status: 200,
          }
        );
      }

      return new Response('', { status: 404 });
    };

    const session: ScraperSession = {
      cookies: [{ name: 'PHPSESSID', value: 'session_concurrency_test' }],
      csrfToken: 'csrf_concurrency_test',
    };

    const result = await fetchProfileData(session);

    assert.strictEqual(result.success, true, 'fetchProfileData should succeed');
    assert.strictEqual(
      totalSubTabRequests,
      9,
      'Should have requested all 9 sub-tabs'
    );
    assert.strictEqual(
      maxConcurrentSeen <= 3,
      true,
      `Peak concurrency was ${maxConcurrentSeen}, which must be <= 3`
    );
    assert.strictEqual(
      maxConcurrentSeen,
      3,
      'Peak concurrency should reach exactly 3 for a 9-item pool with BATCH_SIZE=3'
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
