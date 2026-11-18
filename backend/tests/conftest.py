import os
import tempfile

_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db}")  # CI also runs this suite on PostgreSQL
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SPOTIFY_CLIENT_ID"] = "cid"
os.environ["SPOTIFY_CLIENT_SECRET"] = "csecret"
os.environ["AI_FILTER_URL"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from classpulse.db import Base, engine  # noqa: E402
from classpulse.filter.engine import recent  # noqa: E402
from classpulse.main import create_app  # noqa: E402
from classpulse.security import limiter  # noqa: E402

Base.metadata.create_all(engine)
HDR = {"X-Requested-With": "classpulse"}


@pytest.fixture(autouse=True)
def clean():
    with engine.begin() as conn:
        for t in reversed(Base.metadata.sorted_tables):
            conn.execute(t.delete())
    limiter.reset()
    recent.seen.clear()
    yield


def make_client() -> TestClient:
    c = TestClient(create_app(production=False))
    c.headers.update(HDR)
    return c


@pytest.fixture
def client():
    with make_client() as c:
        yield c


@pytest.fixture
def teacher(client):
    r = client.post("/api/auth/register", json={"email": "t@school.de", "password": "geheim123", "name": "T"})
    assert r.status_code == 200, r.text
    return client


@pytest.fixture
def session(teacher):
    return teacher.post("/api/sessions", json={"title": "7b Mathe"}).json()


@pytest.fixture
def student(session):
    """A second client without any teacher cookie."""
    with make_client() as c:
        tok = c.post(f"/api/p/{session['code']}/join").json()["token"]
        c.headers["X-Participant"] = tok
        c.code = session["code"]
        yield c


def new_student(code):
    c = make_client()
    c.headers["X-Participant"] = c.post(f"/api/p/{code}/join").json()["token"]
    return c
