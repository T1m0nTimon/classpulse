import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import delete, or_, select

from . import auth, participant, spotify, teacher
from .config import get_settings
from .db import SessionLocal
from .models import AuthToken, ClassSession, now
from .realtime import hub
from .security import sha256

log = logging.getLogger("classpulse")


def run_migrations():
    from alembic.config import Config

    from alembic import command

    here = Path(__file__).resolve().parent.parent
    cfg = Config(str(here / "alembic.ini"))
    cfg.set_main_option("script_location", str(here / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(cfg, "head")


def cleanup() -> int:
    """Data minimisation: delete sessions (and all their content) after the retention period."""
    cutoff = now() - timedelta(days=get_settings().data_retention_days)
    with SessionLocal() as db:
        old = db.scalars(select(ClassSession).where(
            or_(ClassSession.ended_at < cutoff, ClassSession.expires_at < cutoff))).all()
        for cs in old:
            db.delete(cs)
        db.execute(delete(AuthToken).where(AuthToken.expires_at < now()))
        db.commit()
        return len(old)


async def _cleanup_loop():
    while True:
        try:
            await asyncio.to_thread(cleanup)
        except Exception:  # noqa: BLE001
            log.exception("cleanup failed")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not app.state.production:  # tests create tables themselves and call cleanup() directly
        yield
        return
    run_migrations()
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def create_app(production: bool = True) -> FastAPI:
    app = FastAPI(title="ClassPulse", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.production = production

    @app.middleware("http")
    async def security(request: Request, call_next):
        # CSRF: state-changing API calls must carry a custom header. Browsers cannot send it
        # cross-site without a CORS preflight, which this app never allows. Cookies are SameSite=Lax too.
        if (request.method not in ("GET", "HEAD", "OPTIONS") and request.url.path.startswith("/api/")
                and request.headers.get("x-requested-with") != "classpulse"):
            return JSONResponse({"detail": "csrf"}, status_code=403)
        response = await call_next(request)
        h = response.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "same-origin"
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        h["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: https://i.scdn.co https://*.spotifycdn.com; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        if get_settings().secure_cookies:
            h["Strict-Transport-Security"] = "max-age=31536000"
        if request.url.path.startswith("/api/"):
            h.setdefault("Cache-Control", "no-store")
        return response

    app.include_router(auth.router)
    app.include_router(teacher.router)
    app.include_router(participant.router)
    app.include_router(spotify.router)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.websocket("/ws/p/{code}")
    async def ws_participant(ws: WebSocket, code: str):
        with SessionLocal() as db:
            c = participant.normalize_code(code)
            cs = db.scalar(select(ClassSession).where(ClassSession.code == c)) if c else None
            sid = cs.id if cs else None
        if not sid:
            await ws.close(code=4404)
            return
        await ws.accept()
        room = f"p:{sid}"
        await hub.join(room, ws)
        await hub.participants_changed(sid)
        try:
            while True:
                await ws.receive_text()  # client pings keep mobile connections alive
        except WebSocketDisconnect:
            pass
        finally:
            hub.leave(room, ws)
            await hub.participants_changed(sid)

    @app.websocket("/ws/t/{session_id}")
    async def ws_teacher(ws: WebSocket, session_id: str):
        origin = ws.headers.get("origin")
        if origin and urlparse(origin).netloc != ws.headers.get("host"):
            await ws.close(code=4403)  # cross-site WebSocket hijacking protection
            return
        token = ws.cookies.get(auth.COOKIE)
        with SessionLocal() as db:
            tok = db.get(AuthToken, sha256(token)) if token else None
            cs = db.get(ClassSession, session_id)
            ok = tok and tok.expires_at > now() and cs and cs.teacher_id == tok.teacher_id
        if not ok:
            await ws.close(code=4401)
            return
        await ws.accept()
        room = f"t:{session_id}"
        await hub.join(room, ws)
        await ws.send_json({"type": "participants", "count": hub.count(f"p:{session_id}")})
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            hub.leave(room, ws)

    # ---- single-page frontend ----
    dist = (Path(__file__).resolve().parent.parent / get_settings().frontend_dist).resolve()
    if (dist / "index.html").exists():

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith(("api/", "ws/")):
                return JSONResponse({"detail": "not_found"}, status_code=404)
            f = (dist / path).resolve()
            if path and f.is_file() and f.is_relative_to(dist):
                cache = "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
                return FileResponse(f, headers={"Cache-Control": cache})
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
