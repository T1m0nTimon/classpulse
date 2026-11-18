# Security Policy

## Reporting a vulnerability

Please **do not open a public issue**. Use GitHub's private vulnerability reporting ("Security" tab → "Report a vulnerability"). We aim to respond within 7 days.

## Security model

| Area | Measure |
|---|---|
| Teacher passwords | scrypt (N=2^15, r=8, p=1), per-password salt, constant-time comparison, dummy hash for unknown emails |
| Teacher sessions | random 256-bit token in an HttpOnly, SameSite=Lax cookie (Secure behind HTTPS); only its SHA-256 is stored; revoked on logout |
| Brute force | per-IP rate limits; max. 8 failed logins per account per 15 minutes |
| CSRF | every state-changing API call requires the `X-Requested-With: classpulse` header (forces a CORS preflight that is never granted) + SameSite cookies |
| XSS | React escaping, no `dangerouslySetInnerHTML`, strict Content-Security-Policy (`script-src 'self'`), `nosniff`, `frame-ancestors 'none'` |
| SQL injection | SQLAlchemy ORM with bound parameters only |
| Authorization | every teacher route checks session ownership (404 for foreign sessions); students only reach activities of the session whose code they hold |
| Session codes | 7 characters from a 31-character alphabet (`secrets`), ~34 bits; wrong codes are rate limited (30 per 5 minutes per IP); sessions expire |
| IDs | 128-bit random URL-safe IDs, never sequential |
| WebSockets | teacher sockets require the auth cookie and a matching `Origin`; student sockets only receive "something changed" signals |
| Spotify OAuth | Authorization Code flow on the server, `state` verified against an HttpOnly cookie, client secret never sent to the browser |
| Input validation | Pydantic models, length limits, content filter on all free text |
| Secrets | only via environment variables / `.env` (git-ignored) |

## Known limitations

- Rate limiting and live updates live in process memory: run a **single** worker (the default). Multiple workers would need Redis.
- Spotify access/refresh tokens are stored unencrypted in the database. Protect database backups accordingly.
- Double-vote prevention is per device (see docs/privacy.md); it is a fairness measure, not a security boundary.
