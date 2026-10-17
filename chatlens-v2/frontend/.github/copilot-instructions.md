# KL Sync GitHub Copilot Instructions

## Project Overview

KL Sync (v2.4.0) is a proprietary, stateless edge proxy dashboard application. It provides an intuitive interface for 11 dashboard modules (Overview, Attendance, Timetable, Marks, etc.) with multi-language (i18n) support. It operates entirely without a database, instead leveraging real-time data scraping and edge proxying, heavily focusing on performance, accessibility, and zero bloat (the "Ponytail Philosophy").

## Code Style Rules

- **TypeScript**: Strict TypeScript 5.8. NEVER use `any`, prefer `unknown`.
- **Styling**: Tailwind CSS v4 + Vanilla CSS tokens. NEVER use inline styles or CSS-in-JS.
- **Icons**: ALWAYS use `@/components/ui/icons` (native SVG library). NEVER suggest external icon libraries.
- **Imports**: Always use `@/` path aliases.

## Banned Dependencies (NEVER SUGGEST)

lucide-react, heroicons, react-icons, swr, tanstack-query, clsx, classnames, tailwind-merge, framer-motion, motion, axios, lodash, underscore, moment, dayjs, date-fns, jest, vitest, mocha, crypto-js, bcrypt, express, fastify, prisma, drizzle, mongoose

## Architecture Constraints

- **Stateless**: No database, no ORM, no persistent storage.
- **Session**: Managed via AES-256-GCM encrypted tokens (Web Crypto API).
- **Environment**: Vercel serverless edge functions.

## Generation Guidelines

- **Imports**: Avoid banned dependencies. Prefer Node standard library where possible.
- **Components**: Ensure WCAG 2.2 AAA compliance (contrast >= 7.1:1, touch targets >= 44px). Do not use default exports for non-page components.
- **Tests**: Generate tests using the native Node.js test runner (`node:test`), NOT Jest or Vitest.
- **API Routes**: Ensure edge proxy routes validate SSRF origins and utilize session encryption properly.
- **Security**: NEVER suggest storing plaintext credentials or hardcoding secrets.
