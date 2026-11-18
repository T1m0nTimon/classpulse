# ClassPulse

**An anonymous, open-source classroom interaction platform for polls, questions, ideas and music.**

A teacher creates a session, projects the QR code, and students join from their phones — no accounts, no names, no app install. Built to be usable by any teacher in under 30 seconds, on a laptop, iPad or classroom PC.

> Screenshots: _placeholders — add `docs/screenshots/teacher.png`, `student.png`, `projector.png` after your first run._

## Features

| | |
|---|---|
| 📊 **Polls** | Single choice, multiple choice, yes/no, scale 1–10, free text, ranking, plus a 🎲 random-question button. Live bar charts with percentages; results shown live or only after closing. |
| 🙋 **Anonymous Q&A** | Students ask questions; teacher approves, rejects, answers, marks as done; students upvote. Sort by top or newest. |
| 💡 **Idea collection** | Trip destinations, project topics, class activities — anonymous submissions with voting. Duplicate ideas are merged into a vote. |
| 🎵 **Music wishes** | Spotify search, cover art, duplicate detection, upvotes, teacher approval, automatic sync to a Spotify playlist, explicit-song filter. Works without Spotify as plain-text wishes. |
| 🏆 **Quiz** | Multiple choice / true-false, per-question timer, speed-based points, live answer stats, anonymous leaderboard; each student sees their own rank. |
| ⚡ **Live** | WebSockets push every change instantly; robust reconnect on iPhone/iPad sleep. |
| 🖥 **Projector view** | Full-screen QR + code, or any activity's live results with a small QR in the corner. |
| 🛡 **Content filter** | Server-side, multilingual (DE/EN), obfuscation-aware, three strictness levels, per-session block/allow words, optional AI second opinion. |
| 🌍 **i18n** | German and English UI; one file to add a language. |
| 🌓 **Light & dark** | Follows the device setting. Responsive from iPhone SE to projector. |

## Quick start

### Docker (recommended)

```bash
cp .env.example .env
# set SECRET_KEY in .env, e.g. python -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose up -d app
```

Open <http://localhost:8000>, create an account, start a session.

### Without Docker (laptop, Raspberry Pi, Linux, macOS)

Requirements: Python 3.11+, Node.js 20+.

```bash
scripts/install.sh      # Windows: scripts\install.ps1
scripts/start.sh        # Windows: scripts\start.ps1
```

**On a laptop in class:** phones cannot open `localhost`. ClassPulse detects this and shows the laptop's network address (e.g. `http://192.168.1.20:8000`) — open that address once and the QR code points to it. Students must be on the same Wi-Fi, and the Wi-Fi must allow devices to reach each other (many school networks don't: use a server, see below).

### Public server with HTTPS (VPS)

Point a domain to your server, then in `.env` set `DOMAIN`, `PUBLIC_URL=https://your.domain`, `SECURE_COOKIES=true`, `POSTGRES_PASSWORD`, and
`DATABASE_URL=postgresql+psycopg://classpulse:<POSTGRES_PASSWORD>@db:5432/classpulse`, then:

```bash
docker compose --profile prod up -d
```

Caddy obtains a Let's Encrypt certificate automatically. Details: [docs/deployment.md](docs/deployment.md).

## Configuration

All settings are environment variables — see [.env.example](.env.example).

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | **Required.** Keys anonymous vote pseudonyms and login tokens. |
| `PUBLIC_URL` | Address in QR codes. Empty = current browser address. |
| `SECURE_COOKIES` | `true` behind HTTPS. |
| `DATABASE_URL` | Empty = SQLite. PostgreSQL: `postgresql+psycopg://…` |
| `ALLOW_REGISTRATION` | `false` to stop new teacher accounts. |
| `SESSION_HOURS` | How long a session stays open (default 12). |
| `DATA_RETENTION_DAYS` | Ended sessions and all their content are deleted after this (default 30). |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | Optional, see [docs/spotify.md](docs/spotify.md). |
| `AI_FILTER_URL` / `AI_FILTER_MODEL` / `AI_FILTER_API_KEY` | Optional AI moderation, see [docs/content-filter.md](docs/content-filter.md). |

## What is free, what needs external services

| Feature | Needs |
|---|---|
| Everything except Spotify sync and AI filter | Nothing — runs fully offline on your own machine. |
| Students joining from mobile data | A server reachable from the internet (any small VPS, ~3–5 €/month). |
| Spotify search + playlist sync | A free Spotify developer app; **the app owner needs Spotify Premium** (Spotify rule since 2026). |
| AI content filter | Optional. Free with a local [Ollama](https://ollama.com) model, or any paid OpenAI-compatible API. |

## Privacy

Short version: **no student accounts, no names, no IP addresses in the database, no tracking, no third-party scripts.** Teachers can never see who wrote or voted what. Read the honest, detailed version including the limits in [docs/privacy.md](docs/privacy.md).

## Security

scrypt password hashes, HttpOnly SameSite cookies with server-side revocable tokens, CSRF header check, strict CSP, ownership checks on every teacher route, rate limiting and login lockout, unguessable 7-character session codes and 128-bit IDs, Origin-checked WebSockets, OAuth state verification, secrets only in environment variables. See [SECURITY.md](SECURITY.md).

## Development

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn classpulse.main:app --reload        # API on :8000
cd frontend && npm install && npm run dev             # UI on :5173 (proxies /api and /ws)
cd backend && .venv/bin/pytest                        # tests
```

Architecture: FastAPI + SQLAlchemy + Alembic (backend), React + Vite + Tailwind (frontend), WebSockets for live events. See [docs/architecture.md](docs/architecture.md).

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). New UI languages are especially easy: copy one object in `frontend/src/i18n.tsx`.

## License

[MIT](LICENSE)
