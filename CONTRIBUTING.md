# Contributing to ClassPulse

Thanks for helping! A few ground rules keep ClassPulse simple and trustworthy.

## Principles

1. **A teacher with no technical background must manage everything in two clicks.** New options need a sensible default and must not clutter the main screens.
2. **Anonymity is not negotiable.** Never add data that could identify a student: no IPs, user agents, fingerprints or cross-activity identifiers in the database or in teacher-facing responses. `tests/test_api.py::test_teacher_never_sees_participant_identifiers` must keep passing.
3. **No third-party tracking, CDNs or analytics.** Everything is served from the instance itself.
4. **No fake features.** Every button does something real; unavailable integrations show a clear message.

## Setup

See "Development" in the README. Before opening a PR:

```bash
cd backend && ruff check classpulse tests && pytest -q
cd frontend && npm run build
```

## Adding a UI language

Copy the `en` object in `frontend/src/i18n.tsx`, translate the values, add it to `languages`, and add the language to the switch in `pages/Home.tsx`. TypeScript will tell you if a key is missing.

## Extending the content filter

Add terms to `backend/classpulse/filter/wordlists.py` in natural spelling (normalisation is automatic) and add a test case in `tests/test_filter.py` — both one that must be blocked and a harmless word that must still pass.

## Database changes

Change `models.py`, then create a migration:

```bash
cd backend && alembic revision --autogenerate -m "describe change"
```
