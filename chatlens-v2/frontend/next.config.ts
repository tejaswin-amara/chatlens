import type { NextConfig } from 'next';

const securityHeaders = [
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=(), payment=()',
  },
  { key: 'Cross-Origin-Opener-Policy', value: 'same-origin' },
  { key: 'Cross-Origin-Resource-Policy', value: 'same-site' },
  { key: 'X-DNS-Prefetch-Control', value: 'off' },
  {
    // TODO: enforce CSP (remove -Report-Only) and add nonce-based script-src once
    // Next.js middleware nonce injection is stable. See: https://nextjs.org/docs/app/api-reference/functions/generate-metadata#content-security-policy
    key: 'Content-Security-Policy-Report-Only',
    value:
      "default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; img-src 'self' data: blob:; font-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self' https://newerp.kluniversity.in https://api.ocr.space; worker-src 'self' blob:",
  },
];

const nextConfig: NextConfig = {
  serverExternalPackages: ['capjs-core', 'esbuild'],
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          ...securityHeaders,
          { key: 'Cache-Control', value: 'private, no-store, max-age=0' },
          { key: 'Vary', value: 'Cookie' },
        ],
      },
      {
        source: '/(.*)',
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
