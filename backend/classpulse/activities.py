"""Activity configuration validation, results and (privacy-safe) serialisation."""

import time
from collections import Counter

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Activity, Response, Submission, SubmissionVote

KINDS = {"poll", "questions", "ideas", "music", "quiz"}
POLL_TYPES = {"single", "multi", "yesno", "scale", "text", "ranking"}


class QuizQuestion(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    options: list[str] = Field(min_length=2, max_length=6)
    correct: list[int] = Field(min_length=1)
    seconds: int = Field(default=20, ge=5, le=300)

    @field_validator("options")
    @classmethod
    def _opts(cls, v):
        v = [o.strip()[:120] for o in v]
        if any(not o for o in v):
            raise ValueError("empty option")
        return v


class ActivityIn(BaseModel):
    kind: str
    title: str = Field(min_length=1, max_length=300)
    # poll
    poll_type: str = "single"
    options: list[str] = Field(default_factory=list, max_length=12)
    results: str = "live"  # live | after
    # questions / ideas / music
    moderation: bool | None = None
    # music
    sync_spotify: bool = True
    allow_explicit: bool = False
    # quiz
    questions: list[QuizQuestion] = Field(default_factory=list, max_length=50)

    @field_validator("kind")
    @classmethod
    def _kind(cls, v):
        if v not in KINDS:
            raise ValueError("unknown kind")
        return v


def build_config(data: ActivityIn) -> dict:
    if data.kind == "poll":
        if data.poll_type not in POLL_TYPES:
            raise HTTPException(422, "invalid_poll_type")
        options = [o.strip()[:120] for o in data.options if o.strip()]
        if data.poll_type in ("single", "multi", "ranking") and len(options) < 2:
            raise HTTPException(422, "need_two_options")
        if data.poll_type == "yesno":
            options = options[:2] if len(options) == 2 else ["Ja", "Nein"]
        if data.poll_type in ("scale", "text"):
            options = []
        return {"poll_type": data.poll_type, "options": options,
                "results": "after" if data.results == "after" else "live"}
    if data.kind == "quiz":
        if not data.questions:
            raise HTTPException(422, "need_questions")
        for q in data.questions:
            if any(i < 0 or i >= len(q.options) for i in q.correct):
                raise HTTPException(422, "invalid_correct_option")
        return {"questions": [q.model_dump() for q in data.questions]}
    default_mod = data.kind in ("questions", "music")
    cfg = {"moderation": default_mod if data.moderation is None else data.moderation}
    if data.kind == "music":
        cfg.update(sync_spotify=data.sync_spotify, allow_explicit=data.allow_explicit)
    return cfg


def initial_state(kind: str) -> dict:
    return {"phase": "waiting", "current": -1, "started_at": 0.0} if kind == "quiz" else {}


# ---------- votes ----------

def validate_vote(activity: Activity, payload: dict) -> dict:
    cfg = activity.config
    t = cfg["poll_type"]
    n = len(cfg["options"])
    try:
        if t in ("single", "yesno"):
            choice = int(payload["choice"])
            if not 0 <= choice < n:
                raise ValueError
            return {"choice": choice}
        if t == "multi":
            choices = sorted({int(c) for c in payload["choices"]})
            if not choices or any(not 0 <= c < n for c in choices):
                raise ValueError
            return {"choices": choices}
        if t == "scale":
            value = int(payload["value"])
            if not 1 <= value <= 10:
                raise ValueError
            return {"value": value}
        if t == "ranking":
            order = [int(i) for i in payload["order"]]
            if sorted(order) != list(range(n)):
                raise ValueError
            return {"order": order}
        if t == "text":
            text = str(payload["text"]).strip()
            if not text:
                raise ValueError
            return {"text": text[:300]}
    except (KeyError, TypeError, ValueError):
        pass
    raise HTTPException(422, "invalid_vote")


def poll_results(db: Session, activity: Activity) -> dict:
    cfg = activity.config
    t = cfg["poll_type"]
    rows = [r.payload for r in db.scalars(select(Response).where(Response.activity_id == activity.id))]
    total = len(rows)
    out: dict = {"total": total}
    if t in ("single", "yesno"):
        c = Counter(r["choice"] for r in rows)
        out["counts"] = [c.get(i, 0) for i in range(len(cfg["options"]))]
    elif t == "multi":
        c = Counter(ch for r in rows for ch in r["choices"])
        out["counts"] = [c.get(i, 0) for i in range(len(cfg["options"]))]
    elif t == "scale":
        c = Counter(r["value"] for r in rows)
        out["counts"] = [c.get(i, 0) for i in range(1, 11)]
        out["average"] = round(sum(r["value"] for r in rows) / total, 1) if total else None
    elif t == "ranking":
        n = len(cfg["options"])
        points = [0] * n  # Borda count: first place gets n-1 points
        for r in rows:
            for pos, idx in enumerate(r["order"]):
                points[idx] += n - 1 - pos
        out["points"] = points
        out["avg_rank"] = [
            round(sum(r["order"].index(i) + 1 for r in rows) / total, 2) if total else None for i in range(n)
        ]
    elif t == "text":
        # newest first; texts only, no ordering metadata that could hint at who wrote what
        out["texts"] = [r["text"] for r in reversed(rows)][:500]
    return out


# ---------- quiz ----------

def quiz_points(correct: bool, elapsed: float, seconds: int) -> int:
    if not correct:
        return 0
    return int(500 + 500 * max(0.0, 1 - elapsed / seconds))


def quiz_results(db: Session, activity: Activity, voter: str | None = None) -> dict:
    qs = activity.config["questions"]
    st = activity.state
    rows = list(db.scalars(select(Response).where(Response.activity_id == activity.id)))
    per_q = []
    for i, q in enumerate(qs):
        answers = [r.payload for r in rows if r.slot == i]
        c = Counter(a["choice"] for a in answers)
        per_q.append({
            "answers": len(answers),
            "counts": [c.get(j, 0) for j in range(len(q["options"]))],
            "correct_count": sum(1 for a in answers if a["correct"]),
        })
    scores = Counter()
    for r in rows:
        scores[r.voter] += r.payload["points"]
    ranking = sorted(scores.values(), reverse=True)
    out = {"phase": st.get("phase"), "current": st.get("current"), "per_question": per_q,
           "top_scores": ranking[:10], "players": len(scores)}
    if voter is not None:
        mine = scores.get(voter, 0)
        out["my_score"] = mine
        out["my_rank"] = (ranking.index(mine) + 1) if voter in scores else None
        out["my_answers"] = {r.slot: r.payload["choice"] for r in rows if r.voter == voter}
    return out


def quiz_public_question(activity: Activity) -> dict | None:
    st = activity.state
    if st.get("phase") not in ("question", "reveal"):
        return None
    q = activity.config["questions"][st["current"]]
    remaining = max(0, q["seconds"] - (time.time() - st["started_at"]))
    data = {"index": st["current"], "count": len(activity.config["questions"]), "text": q["text"],
            "options": q["options"], "seconds": q["seconds"], "remaining": round(remaining, 1)}
    if st["phase"] == "reveal":
        data["correct"] = q["correct"]
    return data


# ---------- submissions ----------

def submission_dict(s: Submission, teacher: bool, voted: set[str] | None = None) -> dict:
    d = {"id": s.id, "text": s.text, "song": s.song, "status": s.status, "answer": s.answer,
         "votes": s.votes, "created_at": s.created_at.isoformat()}
    if teacher:
        d["in_playlist"] = s.in_playlist
    if voted is not None:
        d["voted"] = s.id in voted
    return d


def submissions(db: Session, activity: Activity, teacher: bool, voter: str | None = None) -> list[dict]:
    q = select(Submission).where(Submission.activity_id == activity.id)
    if not teacher:
        q = q.where(Submission.status.in_(["approved", "done"]))
    rows = list(db.scalars(q.order_by(Submission.votes.desc(), Submission.created_at.desc())))
    voted = None
    if voter:
        voted = set(db.scalars(
            select(SubmissionVote.submission_id).where(
                SubmissionVote.voter == voter, SubmissionVote.submission_id.in_([r.id for r in rows])
            )
        ))
    return [submission_dict(r, teacher, voted) for r in rows]


def has_voted(db: Session, activity_id: str, voter: str) -> bool:
    return bool(db.scalar(select(func.count()).select_from(Response).where(
        Response.activity_id == activity_id, Response.voter == voter)))


def activity_dict(db: Session, a: Activity, teacher: bool, voter: str | None = None) -> dict:
    d = {"id": a.id, "kind": a.kind, "title": a.title, "is_open": a.is_open}
    cfg = a.config
    if a.kind == "poll":
        d.update(poll_type=cfg["poll_type"], options=cfg["options"], results_mode=cfg["results"])
        if teacher or cfg["results"] == "live" or not a.is_open:
            d["results"] = poll_results(db, a)
        if voter:
            d["voted"] = has_voted(db, a.id, voter)
    elif a.kind == "quiz":
        if teacher:
            d["questions"] = cfg["questions"]
        d["question"] = quiz_public_question(a)
        d["quiz"] = quiz_results(db, a, voter)
        if not teacher and a.state.get("phase") not in ("reveal", "finished"):
            d["quiz"].pop("per_question")  # no live answer counts while a question is running
    else:
        d["moderation"] = cfg.get("moderation", False)
        if a.kind == "music":
            d["allow_explicit"] = cfg.get("allow_explicit", False)
            if teacher:
                d["sync_spotify"] = cfg.get("sync_spotify", False)
                d["playlist_url"] = cfg.get("playlist_url")
                d["spotify_error"] = a.state.get("spotify_error")
        d["items"] = submissions(db, a, teacher, voter)
    return d
