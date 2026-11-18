"""Database models.

Privacy by design: there is no participant table. Student contributions carry no IP, no user agent
and no participant id. The only link to a participant is `voter`, an HMAC of a random device token
scoped to ONE activity, used solely to stop double voting. It is never sent to teachers and cannot be
linked across activities.
"""

import secrets
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, TypeDecorator, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return secrets.token_urlsafe(16)


class UTCDateTime(TypeDecorator):
    """SQLite drops tzinfo; normalise everything to aware UTC on the way out."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(8), default="de")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)

    spotify: Mapped["SpotifyAccount | None"] = relationship(
        back_populates="teacher", cascade="all, delete-orphan", uselist=False
    )


class AuthToken(Base):
    __tablename__ = "auth_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())


class SpotifyAccount(Base):
    __tablename__ = "spotify_accounts"
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), primary_key=True)
    spotify_user_id: Mapped[str] = mapped_column(String(128), default="")
    display_name: Mapped[str] = mapped_column(String(200), default="")
    # shortcut: tokens stored in plain text in the DB; encrypt at rest if the DB is shared/untrusted.
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())

    teacher: Mapped[Teacher] = relationship(back_populates="spotify")


class ClassSession(Base):
    __tablename__ = "class_sessions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="live")  # live | paused | ended
    filter_level: Mapped[str] = mapped_column(String(16), default="medium")  # low | medium | high
    blocked_words: Mapped[list] = mapped_column(JSON, default=list)
    allowed_words: Mapped[list] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)

    activities: Mapped[list["Activity"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Activity.position"
    )


class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("class_sessions.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # poll | questions | ideas | music | quiz
    title: Mapped[str] = mapped_column(String(300))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[dict] = mapped_column(JSON, default=dict)  # runtime state, e.g. quiz progress
    is_open: Mapped[bool] = mapped_column(default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)

    session: Mapped[ClassSession] = relationship(back_populates="activities")


class Response(Base):
    """A poll vote or quiz answer."""

    __tablename__ = "responses"
    __table_args__ = (UniqueConstraint("activity_id", "voter", "slot"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    voter: Mapped[str] = mapped_column(String(64))
    slot: Mapped[int] = mapped_column(Integer, default=0)  # quiz question index; 0 for polls
    payload: Mapped[dict] = mapped_column(JSON)


class Submission(Base):
    """A question, idea or song wish."""

    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    activity_id: Mapped[str] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    song: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(200), default="", index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|approved|rejected|done
    answer: Mapped[str] = mapped_column(Text, default="")
    votes: Mapped[int] = mapped_column(Integer, default=0)
    in_playlist: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)


class SubmissionVote(Base):
    __tablename__ = "submission_votes"
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), primary_key=True
    )
    voter: Mapped[str] = mapped_column(String(64), primary_key=True)
