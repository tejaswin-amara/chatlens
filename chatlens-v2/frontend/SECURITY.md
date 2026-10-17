# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in KL-Sync, please report it
responsibly:

1. **Email**: Open a private security advisory via GitHub's
   [Security tab](https://github.com/tejaswin-amara/kl-sync/security/advisories/new).
2. **Do not** open a public issue for security vulnerabilities.

We aim to acknowledge reports within 48 hours and provide a fix or
mitigation within 7 days for high-severity issues.

## Scope

- Session encryption (`AES-256-GCM`) and token handling
- SSRF protections in the ERP proxy layer
- Bot-protection bypass (CapJS)
- Client-side data leakage via `localStorage`/`sessionStorage`
