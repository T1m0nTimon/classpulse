import re
import secrets
from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from fastapi import Response as HttpResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import AuthToken, Teacher, now
from .security import hash_password, limiter, rate_limit, sha256, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
COOKIE = "cp_auth"
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Constant-time-ish login for unknown emails: verify against a dummy hash.
_DUMMY_HASH = hash_password(secrets.token_hex(8))


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        v = v.strip().lower()
        if not _EMAIL.match(v):
            raise ValueError("invalid email")
        return v


class Registration(Credentials):
    password: str = Field(min_length=8, max_length=200)
    name: str = Field(default="", max_length=80)
    language: str = "de"


def teacher_dict(t: Teacher) -> dict:
    return {"id": t.id, "email": t.email, "name": t.name, "language": t.language}


def _issue(db: Session, response: HttpResponse, teacher: Teacher):
    s = get_settings()
    token = secrets.token_urlsafe(32)
    db.add(AuthToken(token_hash=sha256(token), teacher_id=teacher.id,
                     expires_at=now() + timedelta(days=s.teacher_login_days)))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=s.teacher_login_days * 86400, httponly=True,
                        secure=s.secure_cookies, samesite="lax", path="/")


def current_teacher(cp_auth: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> Teacher:
    if not cp_auth:
        raise HTTPException(401, "not_logged_in")
    tok = db.get(AuthToken, sha256(cp_auth))
    if not tok or tok.expires_at < now():
        raise HTTPException(401, "not_logged_in")
    teacher = db.get(Teacher, tok.teacher_id)
    if not teacher:
        raise HTTPException(401, "not_logged_in")
    return teacher


@router.post("/register")
def register(data: Registration, request: Request, response: HttpResponse, db: Session = Depends(get_db)):
    if not get_settings().allow_registration:
        raise HTTPException(403, "registration_closed")
    rate_limit(request, "register", 10, 3600)
    if db.scalar(select(Teacher).where(Teacher.email == data.email)):
        raise HTTPException(409, "email_taken")
    t = Teacher(email=data.email, name=data.name.strip(), password_hash=hash_password(data.password),
                language="en" if data.language == "en" else "de")
    db.add(t)
    db.commit()
    _issue(db, response, t)
    return teacher_dict(t)


@router.post("/login")
def login(data: Credentials, request: Request, response: HttpResponse, db: Session = Depends(get_db)):
    rate_limit(request, "login", 20, 600)
    # brute force: max 8 failed attempts per account per 15 minutes, regardless of IP
    fail_key = f"loginfail:{sha256(data.email)}"
    if limiter.count(fail_key, 900) >= 8:
        raise HTTPException(429, "rate_limited")
    t = db.scalar(select(Teacher).where(Teacher.email == data.email))
    if not verify_password(data.password, t.password_hash if t else _DUMMY_HASH) or not t:
        limiter.record(fail_key)
        raise HTTPException(401, "wrong_credentials")
    _issue(db, response, t)
    return teacher_dict(t)


@router.post("/logout")
def logout(response: HttpResponse, cp_auth: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if cp_auth:
        db.execute(delete(AuthToken).where(AuthToken.token_hash == sha256(cp_auth)))
        db.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(teacher: Teacher = Depends(current_teacher)):
    return teacher_dict(teacher)


class Profile(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    language: str | None = None


@router.patch("/me")
def update_me(data: Profile, teacher: Teacher = Depends(current_teacher), db: Session = Depends(get_db)):
    if data.name is not None:
        teacher.name = data.name.strip()
    if data.language in ("de", "en"):
        teacher.language = data.language
    db.commit()
    return teacher_dict(teacher)


@router.delete("/me")
def delete_me(response: HttpResponse, teacher: Teacher = Depends(current_teacher), db: Session = Depends(get_db)):
    """Deletes the account and every session, activity and contribution belonging to it."""
    db.delete(teacher)
    db.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}
