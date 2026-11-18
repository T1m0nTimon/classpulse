"""Teacher API. Every route checks that the session belongs to the logged-in teacher."""

import io
import socket
import time
from datetime import timedelta
from urllib.parse import urlparse

import segno
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Response as HttpResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import spotify
from .activities import ActivityIn, activity_dict, build_config, initial_state
from .auth import current_teacher
from .config import get_settings
from .db import get_db
from .models import Activity, ClassSession, Response, Submission, SubmissionVote, Teacher, now
from .realtime import hub
from .security import new_session_code

router = APIRouter(prefix="/api", tags=["teacher"])


def lan_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # no packet is sent; just picks the outgoing interface
            ip = s.getsockname()[0]
            return None if ip.startswith("127.") else ip
    except OSError:
        return None


@router.get("/config")
def public_config(request: Request):
    s = get_settings()
    lan = None
    if not s.public_url:
        ip = lan_ip()
        port = request.url.port
        lan = f"http://{ip}{':' + str(port) if port else ''}" if ip else None
    return {"public_url": s.public_url.rstrip("/") or None, "lan_url": lan,
            "spotify_enabled": s.spotify_enabled, "registration": s.allow_registration,
            "ai_filter": bool(s.ai_filter_url and s.ai_filter_model)}


# ---------- helpers ----------

def owned_session(session_id: str, teacher: Teacher, db: Session) -> ClassSession:
    cs = db.get(ClassSession, session_id)
    if not cs or cs.teacher_id != teacher.id:
        raise HTTPException(404, "not_found")
    return cs


def owned_activity(activity_id: str, teacher: Teacher, db: Session) -> Activity:
    a = db.get(Activity, activity_id)
    if not a or a.session.teacher_id != teacher.id:
        raise HTTPException(404, "not_found")
    return a


def refresh_status(cs: ClassSession) -> None:
    if cs.status != "ended" and cs.expires_at < now():
        cs.status = "ended"
        cs.ended_at = cs.expires_at


def session_dict(db: Session, cs: ClassSession, full: bool = True) -> dict:
    refresh_status(cs)
    d = {"id": cs.id, "title": cs.title, "code": cs.code, "status": cs.status,
         "created_at": cs.created_at.isoformat(), "expires_at": cs.expires_at.isoformat(),
         "participants": hub.count(f"p:{cs.id}"), "activity_count": len(cs.activities)}
    if full:
        d.update(filter_level=cs.filter_level, blocked_words=cs.blocked_words, allowed_words=cs.allowed_words,
                 activities=[activity_dict(db, a, teacher=True) for a in cs.activities])
    return d


async def changed(cs_id: str, activity_id: str | None = None, students: bool = True):
    await hub.notify(cs_id, {"type": "changed", "activity": activity_id}, students=students)


# ---------- sessions ----------

class SessionIn(BaseModel):
    title: str = Field(default="", max_length=120)


@router.get("/sessions")
def list_sessions(teacher: Teacher = Depends(current_teacher), db: Session = Depends(get_db)):
    rows = db.scalars(select(ClassSession).where(ClassSession.teacher_id == teacher.id)
                      .order_by(ClassSession.created_at.desc()).limit(50))
    out = [session_dict(db, cs, full=False) for cs in rows]
    db.commit()
    return out


@router.post("/sessions")
def create_session(data: SessionIn, teacher: Teacher = Depends(current_teacher), db: Session = Depends(get_db)):
    title = data.title.strip() or now().strftime("%d.%m.%Y %H:%M")
    for _ in range(10):
        cs = ClassSession(teacher_id=teacher.id, title=title, code=new_session_code(), status="live",
                          expires_at=now() + timedelta(hours=get_settings().session_hours))
        db.add(cs)
        try:
            db.commit()
            return session_dict(db, cs)
        except IntegrityError:  # code collision, try again
            db.rollback()
    raise HTTPException(500, "code_generation_failed")


@router.get("/sessions/{session_id}")
def get_session(session_id: str, teacher: Teacher = Depends(current_teacher), db: Session = Depends(get_db)):
    cs = owned_session(session_id, teacher, db)
    d = session_dict(db, cs)
    db.commit()
    return d


class SessionPatch(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    status: str | None = None  # live | paused | ended
    filter_level: str | None = None
    blocked_words: list[str] | None = Field(default=None, max_length=200)
    allowed_words: list[str] | None = Field(default=None, max_length=200)


@router.patch("/sessions/{session_id}")
async def update_session(session_id: str, data: SessionPatch, teacher: Teacher = Depends(current_teacher),
                         db: Session = Depends(get_db)):
    cs = owned_session(session_id, teacher, db)
    refresh_status(cs)
    if data.title is not None and data.title.strip():
        cs.title = data.title.strip()
    if data.status in ("live", "paused", "ended"):
        if data.status == "ended":
            cs.ended_at = now()
        elif cs.status == "ended" or cs.expires_at < now() + timedelta(hours=1):
            # re-opening (or extending): fresh time window
            cs.ended_at = None
            cs.expires_at = now() + timedelta(hours=get_settings().session_hours)
        cs.status = data.status
    if data.filter_level in ("low", "medium", "high"):
        cs.filter_level = data.filter_level
    if data.blocked_words is not None:
        cs.blocked_words = sorted({w.strip()[:60] for w in data.blocked_words if w.strip()})
    if data.allowed_words is not None:
        cs.allowed_words = sorted({w.strip()[:60] for w in data.allowed_words if w.strip()})
    db.commit()
    await changed(cs.id)
    return session_dict(db, cs)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, teacher: Teacher = Depends(current_teacher),
                         db: Session = Depends(get_db)):
    cs = owned_session(session_id, teacher, db)
    db.delete(cs)
    db.commit()
    await hub.notify(session_id, {"type": "deleted"})
    return {"ok": True}


@router.get("/sessions/{session_id}/qr.svg")
def qr(session_id: str, base: str = "", teacher: Teacher = Depends(current_teacher),
       db: Session = Depends(get_db)):
    cs = owned_session(session_id, teacher, db)
    root = get_settings().public_url.rstrip("/") or base.rstrip("/")
    u = urlparse(root)
    if u.scheme not in ("http", "https") or not u.netloc:
        raise HTTPException(422, "invalid_base")
    buf = io.BytesIO()
    segno.make(f"{root}/j/{cs.code}", error="m").save(buf, kind="svg", scale=10, border=2, dark="#000",
                                                       light="#fff", xmldecl=False)
    return HttpResponse(buf.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "private, max-age=300"})


# ---------- activities ----------

@router.post("/sessions/{session_id}/activities")
async def add_activity(session_id: str, data: ActivityIn, teacher: Teacher = Depends(current_teacher),
                       db: Session = Depends(get_db)):
    cs = owned_session(session_id, teacher, db)
    if len(cs.activities) >= 50:
        raise HTTPException(422, "too_many_activities")
    config = build_config(data)
    pos = (db.scalar(select(func.max(Activity.position)).where(Activity.session_id == cs.id)) or 0) + 1
    a = Activity(session_id=cs.id, kind=data.kind, title=data.title.strip(), config=config,
                 state=initial_state(data.kind), position=pos)
    if data.kind == "music" and config.get("sync_spotify"):
        acc = teacher.spotify
        if acc and get_settings().spotify_enabled:
            try:
                pl = await run_in_threadpool(spotify.create_playlist, db, acc, f"ClassPulse – {a.title}")
                a.config = {**config, "playlist_id": pl["id"], "playlist_url": pl["url"]}
            except spotify.SpotifyError as e:
                a.state = {"spotify_error": str(e)}
        else:
            a.config = {**config, "sync_spotify": False}
    db.add(a)
    db.commit()
    await changed(cs.id, a.id)
    return activity_dict(db, a, teacher=True)


class ActivityPatch(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    is_open: bool | None = None
    results: str | None = None
    moderation: bool | None = None


@router.patch("/activities/{activity_id}")
async def update_activity(activity_id: str, data: ActivityPatch, teacher: Teacher = Depends(current_teacher),
                          db: Session = Depends(get_db)):
    a = owned_activity(activity_id, teacher, db)
    if data.title and data.title.strip():
        a.title = data.title.strip()
    if data.is_open is not None:
        a.is_open = data.is_open
    if data.results in ("live", "after") and a.kind == "poll":
        a.config = {**a.config, "results": data.results}
    if data.moderation is not None and a.kind in ("questions", "ideas", "music"):
        a.config = {**a.config, "moderation": data.moderation}
    db.commit()
    await changed(a.session_id, a.id)
    return activity_dict(db, a, teacher=True)


@router.delete("/activities/{activity_id}")
async def delete_activity(activity_id: str, teacher: Teacher = Depends(current_teacher),
                          db: Session = Depends(get_db)):
    a = owned_activity(activity_id, teacher, db)
    sid = a.session_id
    db.delete(a)
    db.commit()
    await changed(sid, activity_id)
    return {"ok": True}


@router.post("/activities/{activity_id}/reset")
async def reset_activity(activity_id: str, teacher: Teacher = Depends(current_teacher),
                         db: Session = Depends(get_db)):
    a = owned_activity(activity_id, teacher, db)
    db.execute(delete(Response).where(Response.activity_id == a.id))
    db.execute(delete(Submission).where(Submission.activity_id == a.id))
    a.state = initial_state(a.kind)
    a.is_open = True
    db.commit()
    await changed(a.session_id, a.id)
    return activity_dict(db, a, teacher=True)


# ---------- moderation of questions / ideas / songs ----------

class SubmissionPatch(BaseModel):
    status: str | None = None  # pending | approved | rejected | done
    answer: str | None = Field(default=None, max_length=2000)


def _playlist_sync(db: Session, teacher: Teacher, a: Activity, s: Submission, want: bool):
    """Keep the Spotify playlist in line with approved songs. Errors are reported, never fatal."""
    pid = a.config.get("playlist_id")
    if not (s.song and pid and a.config.get("sync_spotify") and teacher.spotify) or s.in_playlist == want:
        return
    try:
        if want:
            spotify.add_items(db, teacher.spotify, pid, [s.song["uri"]])
        else:
            spotify.remove_items(db, teacher.spotify, pid, [s.song["uri"]])
        s.in_playlist = want
        a.state = {**a.state, "spotify_error": None}
    except spotify.SpotifyError as e:
        a.state = {**a.state, "spotify_error": str(e)}


def owned_submission(sub_id: str, teacher: Teacher, db: Session) -> tuple[Submission, Activity]:
    s = db.get(Submission, sub_id)
    if not s:
        raise HTTPException(404, "not_found")
    return s, owned_activity(s.activity_id, teacher, db)


@router.patch("/submissions/{sub_id}")
async def moderate_submission(sub_id: str, data: SubmissionPatch, teacher: Teacher = Depends(current_teacher),
                              db: Session = Depends(get_db)):
    s, a = owned_submission(sub_id, teacher, db)
    if data.status in ("pending", "approved", "rejected", "done"):
        s.status = data.status
    if data.answer is not None:
        s.answer = data.answer.strip()
    if a.kind == "music":
        await run_in_threadpool(_playlist_sync, db, teacher, a, s, s.status in ("approved", "done"))
    db.commit()
    await changed(a.session_id, a.id)
    return activity_dict(db, a, teacher=True)


@router.delete("/submissions/{sub_id}")
async def delete_submission(sub_id: str, teacher: Teacher = Depends(current_teacher),
                            db: Session = Depends(get_db)):
    s, a = owned_submission(sub_id, teacher, db)
    if a.kind == "music":
        await run_in_threadpool(_playlist_sync, db, teacher, a, s, False)
    db.execute(delete(SubmissionVote).where(SubmissionVote.submission_id == s.id))
    db.delete(s)
    db.commit()
    await changed(a.session_id, a.id)
    return activity_dict(db, a, teacher=True)


# ---------- quiz control ----------

class QuizAction(BaseModel):
    action: str  # next | reveal | finish | restart


@router.post("/activities/{activity_id}/quiz")
async def quiz_control(activity_id: str, data: QuizAction, teacher: Teacher = Depends(current_teacher),
                       db: Session = Depends(get_db)):
    a = owned_activity(activity_id, teacher, db)
    if a.kind != "quiz":
        raise HTTPException(422, "not_a_quiz")
    st = dict(a.state)
    total = len(a.config["questions"])
    if data.action == "next":
        if st["current"] + 1 >= total:
            st["phase"] = "finished"
        else:
            st.update(current=st["current"] + 1, phase="question", started_at=time.time())
    elif data.action == "reveal" and st["phase"] == "question":
        st["phase"] = "reveal"
    elif data.action == "finish":
        st["phase"] = "finished"
    elif data.action == "restart":
        db.execute(delete(Response).where(Response.activity_id == a.id))
        st = initial_state("quiz")
    else:
        raise HTTPException(422, "invalid_action")
    a.state = st
    db.commit()
    await changed(a.session_id, a.id)
    return activity_dict(db, a, teacher=True)
