# TypeScript & Frontend Engineering Rules (ChatLens v2)

## Framework & Architecture
- **Framework**: Next.js 16 App Router with Turbopack.
- **Directory Layout**: Flat component structure (`src/components/`, `src/hooks/`, `src/types.ts`). Do NOT place components or hooks inside `src/app/`.
- **Import Paths**: Always use `@/...` path aliases (e.g., `@/components/Dashboard`, `@/hooks/useApi`, `@/types`).
- **Build Mode**: Static export (`output: "export"` in `next.config.ts`).

## Code Standards & Accessibility
- **Strict Typing**: Zero `any` types. Run `npx tsc --noEmit` before commits.
- **Motion Accessibility (`motion-a11y-audit`)**: Enforce `@media (prefers-reduced-motion: reduce)` in `globals.css` ensuring instantaneous animations and zero motion sickness for sensitive users.
- **Client Components**: Mark interactive UI with `'use client';` at the very top. Keep data-fetching clean.
