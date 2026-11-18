"""Student API: no login, no personal data.

A student device gets a random token from /join and keeps it locally. The server never stores the
token itself, only HMAC(token, activity_id) next to votes, so a vote cannot be linked to a device in
another activity, and teachers never receive these values.
"""

import re
import secrets
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import spotify
from .activities import activity_dict, quiz_points, validate_vote
from .db import get_db
from .filter.engine import dedupe_key, moderate, recent
from .models import Activity, ClassSession, Response, Submission, SubmissionVote, Teacher
from .realtime import hub
from .security import CODE_ALPHABET, rate_limit, sha256, voter_hash
from .teacher import _playlist_sync, refresh_status

router = APIRouter(prefix="/api/p", tags=["participant"])
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{32,64}$")


def normalize_code(code: str) -> str:
    c = code.upper().replace(" ", "").replace("-", "")
    return c if all(ch in CODE_ALPHABET for ch in c) and 4 <= len(c) <= 16 else ""


def get_open_session(code: str, db: Session, request: Request) -> ClassSession:
    rate_limit(request, "lookup", 600, 60)
    c = normalize_code(code)
    cs = db.scalar(select(ClassSession).where(ClassSession.code == c)) if c else None
    if not cs:
        rate_limit(request, "badcode", 30, 300)  # guessing protection
        raise HTTPException(404, "session_not_found")
    refresh_status(cs)
    return cs


def participant_token(x_participant: str = Header(default="")) -> str:
    if not _TOKEN.match(x_participant):
        raise HTTPException(401, "missing_participant_token")
    return x_participant


def active_activity(cs: ClassSession, activity_id: str) -> Activity:
    if cs.status == "ended":
        raise HTTPException(410, "session_ended")
    if cs.status == "paused":
        raise HTTPException(423, "session_paused")
    a = next((x for x in cs.activities if x.id == activity_id), None)
    if not a:
        raise HTTPException(404, "not_found")
    if not a.is_open:
        raise HTTPException(423, "activity_closed")
    return a


@router.post("/{code}/join")
def join(code: str, request: Request, db: Session = Depends(get_db)):
    cs = get_open_session(code, db, request)
    if cs.status == "ended":
        raise HTTPException(410, "session_ended")
    return {"token": secrets.token_urlsafe(32), "code": cs.code}


@router.get("/{code}")
def view(code: str, request: Request, token: str = Depends(participant_token), db: Session = Depends(get_db)):
    cs = get_open_session(code, db, request)
    teacher = db.get(Teacher, cs.teacher_id)
    data = {"title": cs.title, "code": cs.code, "status": cs.status, "language": teacher.language,
            "spotify": bool(teacher.spotify), "activities": []}
    if cs.status == "live":
        data["activities"] = [activity_dict(db, a, teacher=False, voter=voter_hash(token, a.id))
                              for a in cs.activities]
    db.commit()
    return data


class VoteIn(BaseModel):
    payload: dict


@router.post("/{code}/a/{activity_id}/vote")
async def vote(code: str, activity_id: str, data: VoteIn, request: Request,
               token: str = Depends(participant_token), db: Session = Depends(get_db)):
    rate_limit(request, "vote", 30, 60, extra=sha256(token)[:12])
    cs = get_open_session(code, db, request)
    a = active_activity(cs, activity_id)
    if a.kind != "poll":
        raise HTTPException(422, "not_a_poll")
    payload = validate_vote(a, data.payload)
    if "text" in payload:
        res = await moderate(payload["text"], cs, max_len=300)
        if not res.ok:
            raise HTTPException(422, f"filter:{res.reason}")
    db.add(Response(activity_id=a.id, voter=voter_hash(token, a.id), slot=0, payload=payload))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "already_voted") from None
    await hub.notify(cs.id, {"type": "changed", "activity": a.id},
                     students=a.config["results"] == "live")
    return {"ok": True}


class SubmitIn(BaseModel):
    text: str = Field(default="", max_length=1000)
    track_id: str = Field(default="", max_length=40)


@router.post("/{code}/a/{activity_id}/submit")
async def submit(code: str, activity_id: str, data: SubmitIn, request: Request,
                 token: str = Depends(participant_token), db: Session = Depends(get_db)):
    rate_limit(request, "submit", 6, 60, extra=sha256(token)[:12])
    rate_limit(request, "submit_ip", 300, 60)
    cs = get_open_session(code, db, request)
    a = active_activity(cs, activity_id)
    if a.kind not in ("questions", "ideas", "music"):
        raise HTTPException(422, "not_supported")
    voter = voter_hash(token, a.id)
    teacher = db.get(Teacher, cs.teacher_id)
    song = None
    if a.kind == "music" and data.track_id:
        if not teacher.spotify:
            raise HTTPException(400, "spotify_not_connected")
        try:
            song = await run_in_threadpool(spotify.get_track, db, teacher.spotify, data.track_id)
        except spotify.SpotifyError:
            raise HTTPException(502, "spotify_unavailable") from None
        if song["explicit"] and not a.config.get("allow_explicit"):
            raise HTTPException(422, "filter:explicit")
        text, key = f"{song['name']} – {song['artists']}", f"sp:{song['id']}"
    else:
        res = await moderate(data.text, cs, max_len=300 if a.kind == "music" else 500)
        if not res.ok:
            raise HTTPException(422, f"filter:{res.reason}")
        text, key = data.text.strip(), dedupe_key(data.text)
    if recent.is_repeat(sha256(voter + key)):
        raise HTTPException(422, "filter:duplicate")
    existing = db.scalar(select(Submission).where(Submission.activity_id == a.id, Submission.dedupe_key == key,
                                                  Submission.status != "rejected"))
    if existing:  # same song / same idea already there: count it as an upvote instead
        _add_vote(db, existing, voter)
        db.commit()
        await hub.notify(cs.id, {"type": "changed", "activity": a.id})
        return {"ok": True, "merged": True, "status": existing.status}
    approved = not a.config.get("moderation")
    s = Submission(activity_id=a.id, text=text, song=song, dedupe_key=key,
                   status="approved" if approved else "pending")
    db.add(s)
    db.flush()
    _add_vote(db, s, voter)
    if approved and song:
        await run_in_threadpool(_playlist_sync, db, teacher, a, s, True)
    db.commit()
    await hub.notify(cs.id, {"type": "changed", "activity": a.id}, students=approved)
    return {"ok": True, "merged": False, "status": s.status}


def _add_vote(db: Session, s: Submission, voter: str) -> bool:
    if db.get(SubmissionVote, (s.id, voter)):
        return False
    db.add(SubmissionVote(submission_id=s.id, voter=voter))
    s.votes += 1
    return True


@router.post("/{code}/a/{activity_id}/upvote/{sub_id}")
async def upvote(code: str, activity_id: str, sub_id: str, request: Request,
                 token: str = Depends(participant_token), db: Session = Depends(get_db)):
    rate_limit(request, "upvote", 60, 60, extra=sha256(token)[:12])
    cs = get_open_session(code, db, request)
    a = active_activity(cs, activity_id)
    s = db.get(Submission, sub_id)
    if not s or s.activity_id != a.id or s.status not in ("approved", "done"):
        raise HTTPException(404, "not_found")
    voter = voter_hash(token, a.id)
    existing = db.get(SubmissionVote, (s.id, voter))
    if existing:  # toggle
        db.delete(existing)
        s.votes = max(0, s.votes - 1)
    else:
        _add_vote(db, s, voter)
    db.commit()
    await hub.notify(cs.id, {"type": "changed", "activity": a.id})
    return {"ok": True, "voted": not existing, "votes": s.votes}


class AnswerIn(BaseModel):
    index: int
    choice: int


@router.post("/{code}/a/{activity_id}/answer")
async def quiz_answer(code: str, activity_id: str, data: AnswerIn, request: Request,
                      token: str = Depends(participant_token), db: Session = Depends(get_db)):
    rate_limit(request, "answer", 30, 60, extra=sha256(token)[:12])
    cs = get_open_session(code, db, request)
    a = active_activity(cs, activity_id)
    st = a.state
    if a.kind != "quiz" or st.get("phase") != "question" or st.get("current") != data.index:
        raise HTTPException(409, "question_closed")
    q = a.config["questions"][data.index]
    elapsed = time.time() - st["started_at"]
    if elapsed > q["seconds"] + 1.5:  # small grace for slow mobile networks
        raise HTTPException(409, "time_up")
    if not 0 <= data.choice < len(q["options"]):
        raise HTTPException(422, "invalid_choice")
    correct = data.choice in q["correct"]
    db.add(Response(activity_id=a.id, voter=voter_hash(token, a.id), slot=data.index,
                    payload={"choice": data.choice, "correct": correct,
                             "points": quiz_points(correct, elapsed, q["seconds"])}))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "already_answered") from None
    await hub.notify(cs.id, {"type": "changed", "activity": a.id}, students=False)
    return {"ok": True}


@router.get("/{code}/a/{activity_id}/search")
def song_search(code: str, activity_id: str, q: str, request: Request,
                token: str = Depends(participant_token), db: Session = Depends(get_db)):
    rate_limit(request, "search", 20, 60, extra=sha256(token)[:12])
    rate_limit(request, "search_ip", 600, 60)
    cs = get_open_session(code, db, request)
    a = active_activity(cs, activity_id)
    teacher = db.get(Teacher, cs.teacher_id)
    if a.kind != "music" or not teacher.spotify:
        raise HTTPException(400, "spotify_not_connected")
    if len(q.strip()) < 2:
        return []
    try:
        return spotify.search(db, teacher.spotify, q.strip(), a.config.get("allow_explicit", False))
    except spotify.SpotifyError:
        raise HTTPException(502, "spotify_unavailable") from None
