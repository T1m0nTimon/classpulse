# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/), versioning: [SemVer](https://semver.org/).

## [1.0.0] - 2026-11-18

### Added
- Teacher accounts (email + password), sessions with QR code, join code and link, participant count.
- Session lifecycle: start, pause, end, reopen, delete; automatic expiry and data retention cleanup.
- Polls: single, multiple, yes/no, scale 1–10, free text, ranking, random question; live or after-close results.
- Anonymous Q&A with moderation, answers, done state, upvotes and sorting.
- Idea collection with voting and duplicate merging.
- Music wishes with Spotify search, playlist sync (Feb-2026 Web API endpoints), explicit filter; text fallback without Spotify.
- Quiz with timers, speed-based scoring, reveal, anonymous leaderboard.
- Live updates over WebSockets with iOS-safe reconnect; projector view.
- Server-side content filter (DE/EN, obfuscation-aware, three levels, custom words, optional AI check).
- German and English UI, light/dark mode, PWA manifest and Apple touch icon.
- Docker image, docker-compose with PostgreSQL + Caddy HTTPS profile, install scripts, Alembic migrations, GitHub Actions CI.
