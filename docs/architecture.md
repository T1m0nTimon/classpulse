# Architecture

```
frontend/ (React 19 + Vite + Tailwind 4, TypeScript)
  src/pages/Home.tsx          teacher start page, login, account settings
  src/pages/SessionPage.tsx   teacher session: QR, activities, moderation, projector view
  src/pages/Join.tsx          code entry
  src/pages/Student.tsx       student view (polls, quiz, questions, ideas, music)
  src/live.ts                 WebSocket hook with iOS-safe reconnect
  src/i18n.tsx                translations (de, en)

backend/classpulse/ (FastAPI, SQLAlchemy 2, Alembic, Pydantic)
  main.py          app factory, security headers + CSRF, WebSockets, SPA serving, cleanup job
  auth.py          teacher accounts and cookie sessions
  teacher.py       sessions, activities, moderation, quiz control, QR codes
  participant.py   anonymous student API
  activities.py    activity config validation, results, privacy-safe serialisation
  spotify.py       OAuth + Web API client
  filter/          content filter (engine + word lists)
  realtime.py      in-process WebSocket hub
  security.py      password hashing, pseudonyms, codes, rate limiting
  models.py        database models
```

## Live updates

WebSocket messages carry no content — only `{"type": "changed", "activity": id}` or the participant count. Clients then re-fetch over REST (throttled). This keeps authorization in one place (the REST endpoints) and means a student socket never receives teacher-only data.

## Data model

`Teacher` 1─n `ClassSession` 1─n `Activity` 1─n `Response` (votes/answers) and `Submission` (questions/ideas/songs) 1─n `SubmissionVote`. Activity-specific settings live in `Activity.config` (JSON), runtime state (quiz progress) in `Activity.state`.
