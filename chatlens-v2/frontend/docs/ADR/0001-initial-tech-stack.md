# ADR-0001: Initial Technology Stack Selection

**Status**: Accepted
**Date**: 2026-08-02

## Context

Building an unofficial ERP client for KL University students that proxies a legacy ASP.NET Web Forms application (`newerp.kluniversity.in`). The client must be exceptionally fast, reliable, privacy-respecting, and require low maintenance.

## Decision

We have selected the following technology stack:

- **Next.js 16 App Router + Turbopack**: Provides edge functions, API routes, SSR, and excellent DX.
- **TypeScript 5.8**: Ensures strict mode type safety across the entire application.
- **Tailwind CSS v4**: Utility-first CSS, avoiding heavy custom CSS frameworks or runtime CSS-in-JS.
- **Cheerio**: Lightweight HTML-to-JSON parsing. Selected over headless browsers for speed and lower server resource overhead.
- **Zod**: Runtime schema validation to safely handle inconsistent ERP responses.
- **Web Crypto API AES-256-GCM**: Native, zero-dependency session encryption, avoiding external crypto libraries.
- **Vercel deployment**: Enables serverless edge functions, CDN caching, and zero-config deployment.
- **Native node:test runner**: High-performance testing without the overhead of Jest.
- **Native SVG icon engine**: Custom SVGs with zero runtime, avoiding large icon packs like `lucide-react`.

## Consequences

- Minimal dependency footprint (~8 production dependencies).
- Extremely fast cold starts.
- Low client bundle size, adhering to strict performance budgets.
- Highly maintainable with the "Ponytail Philosophy" (YAGNI, zero bloat, stdlib over deps).

## Alternatives Considered

- **Remix**: Rejected due to no Turbopack equivalent and a smaller ecosystem for serverless deployment optimizations on edge.
- **SWR/TanStack Query**: Rejected as an unnecessary abstraction. A custom simple fetch + cache implementation (`useNativeQuery`) is sufficient and lighter.
- **Jest**: Rejected as it is heavier, slower, and unnecessary for a project of this size. Native Node.js `node:test` is preferred.
- **Puppeteer**: Rejected because it is too heavy for server-side scraping. Cheerio is sufficient for traversing DOM structures from basic HTTP responses.
- **crypto-js**: Rejected because the native Web Crypto API is zero-dependency and widely supported.
