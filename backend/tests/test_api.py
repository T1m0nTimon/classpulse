import json

from conftest import make_client, new_student

from classpulse.security import CODE_ALPHABET

# ---------- auth & permissions ----------

def test_register_login_logout(client):
    r = client.post("/api/auth/register", json={"email": "A@B.de", "password": "longpassword"})
    assert r.status_code == 200 and r.json()["email"] == "a@b.de"
    assert client.get("/api/auth/me").status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "a@b.de", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "a@b.de", "password": "longpassword"}).status_code == 200


def test_register_rejects_short_password_and_duplicate(client):
    assert client.post("/api/auth/register", json={"email": "a@b.de", "password": "short"}).status_code == 422
    client.post("/api/auth/register", json={"email": "a@b.de", "password": "longpassword"})
    assert client.post("/api/auth/register", json={"email": "a@b.de", "password": "longpassword"}).status_code == 409


def test_password_is_hashed():
    from classpulse.security import hash_password, verify_password
    h = hash_password("geheim123")
    assert "geheim123" not in h and h.startswith("scrypt$")
    assert verify_password("geheim123", h) and not verify_password("x", h)


def test_login_brute_force_lockout(client):
    client.post("/api/auth/register", json={"email": "a@b.de", "password": "longpassword"})
    client.post("/api/auth/logout")
    for _ in range(8):
        client.post("/api/auth/login", json={"email": "a@b.de", "password": "nope"})
    r = client.post("/api/auth/login", json={"email": "a@b.de", "password": "longpassword"})
    assert r.status_code == 429


def test_csrf_header_required(teacher):
    del teacher.headers["X-Requested-With"]
    assert teacher.post("/api/sessions", json={}).status_code == 403


def test_teacher_cannot_access_foreign_session(session):
    with make_client() as other:
        other.post("/api/auth/register", json={"email": "o@school.de", "password": "geheim123"})
        assert other.get(f"/api/sessions/{session['id']}").status_code == 404
        assert other.patch(f"/api/sessions/{session['id']}", json={"status": "ended"}).status_code == 404
        assert other.post(f"/api/sessions/{session['id']}/activities",
                          json={"kind": "questions", "title": "x"}).status_code == 404
        assert other.get("/api/sessions").json() == []


def test_requires_login(client):
    assert client.post("/api/sessions", json={}).status_code == 401


# ---------- sessions ----------

def test_session_code_and_qr(teacher, session):
    assert len(session["code"]) == 7 and all(c in CODE_ALPHABET for c in session["code"])
    assert len(session["id"]) >= 20  # not guessable / sequential
    r = teacher.get(f"/api/sessions/{session['id']}/qr.svg", params={"base": "http://192.168.0.5:8000"})
    assert r.status_code == 200 and "<svg" in r.text and "xmlns" in r.text
    assert teacher.get(f"/api/sessions/{session['id']}/qr.svg", params={"base": "javascript:x"}).status_code == 422


def test_session_lifecycle(teacher, session, student):
    sid, code = session["id"], session["code"]
    a = teacher.post(f"/api/sessions/{sid}/activities", json={"kind": "questions", "title": "Fragen"}).json()
    teacher.patch(f"/api/sessions/{sid}", json={"status": "paused"})
    assert student.get(f"/api/p/{code}").json()["status"] == "paused"
    assert student.post(f"/api/p/{code}/a/{a['id']}/submit", json={"text": "Hallo?"}).status_code == 423
    teacher.patch(f"/api/sessions/{sid}", json={"status": "ended"})
    assert student.post(f"/api/p/{code}/join").status_code == 410
    teacher.patch(f"/api/sessions/{sid}", json={"status": "live"})  # reopen
    assert student.post(f"/api/p/{code}/a/{a['id']}/submit", json={"text": "Hallo?"}).status_code == 200
    assert teacher.delete(f"/api/sessions/{sid}").status_code == 200
    assert student.get(f"/api/p/{code}").status_code == 404


def test_unknown_code_and_guessing_rate_limit(client):
    assert client.post("/api/p/ZZZZZZZ/join").status_code == 404
    codes = [client.post("/api/p/ZZZZZZZ/join").status_code for _ in range(40)]
    assert 429 in codes


# ---------- polls ----------

def poll(teacher, session, **kw):
    body = {"kind": "poll", "title": "Lieblingsfach?", "poll_type": "single", "options": ["Mathe", "Deutsch"]}
    body.update(kw)
    return teacher.post(f"/api/sessions/{session['id']}/activities", json=body).json()


def test_single_choice_poll_and_double_vote(teacher, session, student):
    a = poll(teacher, session)
    url = f"/api/p/{student.code}/a/{a['id']}/vote"
    assert student.post(url, json={"payload": {"choice": 1}}).status_code == 200
    assert student.post(url, json={"payload": {"choice": 0}}).status_code == 409  # one vote per device
    with new_student(student.code) as s2:
        assert s2.post(url, json={"payload": {"choice": 1}}).status_code == 200
    res = teacher.get(f"/api/sessions/{session['id']}").json()["activities"][0]["results"]
    assert res == {"total": 2, "counts": [0, 2]}
    assert student.post(url, json={"payload": {"choice": 5}}).status_code in (409, 422)


def test_multi_scale_ranking_yesno(teacher, session, student):
    multi = poll(teacher, session, poll_type="multi", options=["a", "b", "c"])
    scale = poll(teacher, session, poll_type="scale", options=[])
    rank = poll(teacher, session, poll_type="ranking", options=["x", "y", "z"])
    yn = poll(teacher, session, poll_type="yesno", options=[])
    base = f"/api/p/{student.code}/a/"
    assert student.post(base + multi["id"] + "/vote", json={"payload": {"choices": [0, 2]}}).status_code == 200
    assert student.post(base + scale["id"] + "/vote", json={"payload": {"value": 8}}).status_code == 200
    assert student.post(base + rank["id"] + "/vote", json={"payload": {"order": [2, 0, 1]}}).status_code == 200
    assert student.post(base + yn["id"] + "/vote", json={"payload": {"choice": 0}}).status_code == 200
    with new_student(student.code) as s2:
        assert s2.post(base + scale["id"] + "/vote", json={"payload": {"value": 11}}).status_code == 422
        assert s2.post(base + rank["id"] + "/vote", json={"payload": {"order": [0, 0, 1]}}).status_code == 422
    acts = {a["id"]: a for a in teacher.get(f"/api/sessions/{session['id']}").json()["activities"]}
    assert acts[multi["id"]]["results"]["counts"] == [1, 0, 1]
    assert acts[scale["id"]]["results"]["average"] == 8
    assert acts[rank["id"]]["results"]["points"] == [1, 0, 2]
    assert acts[yn["id"]]["options"] == ["Ja", "Nein"]


def test_text_poll_is_filtered(teacher, session, student):
    a = poll(teacher, session, poll_type="text", options=[])
    url = f"/api/p/{student.code}/a/{a['id']}/vote"
    r = student.post(url, json={"payload": {"text": "Du Hurensohn"}})
    assert r.status_code == 422 and r.json()["detail"] == "filter:inappropriate"
    assert student.post(url, json={"payload": {"text": "Bruchrechnung"}}).status_code == 200
    res = teacher.get(f"/api/sessions/{session['id']}").json()["activities"][0]["results"]
    assert res["texts"] == ["Bruchrechnung"]  # rejected text was not stored


def test_results_after_mode_hidden_until_closed(teacher, session, student):
    a = poll(teacher, session, results="after")
    student.post(f"/api/p/{student.code}/a/{a['id']}/vote", json={"payload": {"choice": 0}})
    view = student.get(f"/api/p/{student.code}").json()["activities"][0]
    assert "results" not in view and view["voted"] is True
    teacher.patch(f"/api/activities/{a['id']}", json={"is_open": False})
    view = student.get(f"/api/p/{student.code}").json()["activities"][0]
    assert view["results"]["counts"] == [1, 0]


def test_reset_results(teacher, session, student):
    a = poll(teacher, session)
    student.post(f"/api/p/{student.code}/a/{a['id']}/vote", json={"payload": {"choice": 0}})
    r = teacher.post(f"/api/activities/{a['id']}/reset").json()
    assert r["results"]["total"] == 0


# ---------- questions & ideas ----------

def test_questions_moderation_flow(teacher, session, student):
    a = teacher.post(f"/api/sessions/{session['id']}/activities", json={"kind": "questions", "title": "F"}).json()
    url = f"/api/p/{student.code}/a/{a['id']}/submit"
    r = student.post(url, json={"text": "Was kommt in der Arbeit dran?"})
    assert r.json()["status"] == "pending"
    assert student.get(f"/api/p/{student.code}").json()["activities"][0]["items"] == []  # not yet visible
    item = teacher.get(f"/api/sessions/{session['id']}").json()["activities"][0]["items"][0]
    teacher.patch(f"/api/submissions/{item['id']}", json={"status": "approved", "answer": "Kapitel 3"})
    items = student.get(f"/api/p/{student.code}").json()["activities"][0]["items"]
    assert items[0]["answer"] == "Kapitel 3"
    # blocked content
    r = student.post(url, json={"text": "du bist ein h.u.r.e.n.s.o.h.n"})
    assert r.status_code == 422 and r.json()["detail"] == "filter:inappropriate"
    # repeat of the same text is rejected as duplicate
    assert student.post(url, json={"text": "Was kommt in der Arbeit dran?"}).json()["detail"] == "filter:duplicate"


def test_ideas_upvote_toggle_and_dedupe(teacher, session, student):
    a = teacher.post(f"/api/sessions/{session['id']}/activities", json={"kind": "ideas", "title": "Ausflug"}).json()
    student.post(f"/api/p/{student.code}/a/{a['id']}/submit", json={"text": "Zoo"})
    with new_student(student.code) as s2:
        r = s2.post(f"/api/p/{student.code}/a/{a['id']}/submit", json={"text": "zoo!"})
        assert r.json()["merged"] is True  # same idea counted as vote
        item = s2.get(f"/api/p/{student.code}").json()["activities"][0]["items"][0]
        assert item["votes"] == 2 and item["voted"] is True
        r = s2.post(f"/api/p/{student.code}/a/{a['id']}/upvote/{item['id']}").json()
        assert r == {"ok": True, "voted": False, "votes": 1}


# ---------- quiz ----------

def test_quiz_flow_and_scoring(teacher, session, student):
    q = {"kind": "quiz", "title": "Hauptstädte", "questions": [
        {"text": "Hauptstadt von Frankreich?", "options": ["Paris", "Rom"], "correct": [0], "seconds": 20},
        {"text": "2+2?", "options": ["3", "4"], "correct": [1], "seconds": 10}]}
    a = teacher.post(f"/api/sessions/{session['id']}/activities", json=q).json()
    url = f"/api/p/{student.code}/a/{a['id']}/answer"
    assert student.post(url, json={"index": 0, "choice": 0}).status_code == 409  # not started
    teacher.post(f"/api/activities/{a['id']}/quiz", json={"action": "next"})
    view = student.get(f"/api/p/{student.code}").json()["activities"][0]
    assert view["question"]["text"] == "Hauptstadt von Frankreich?" and "correct" not in view["question"]
    assert "questions" not in view  # students never see answers in advance
    assert student.post(url, json={"index": 0, "choice": 0}).status_code == 200
    assert student.post(url, json={"index": 0, "choice": 1}).status_code == 409
    teacher.post(f"/api/activities/{a['id']}/quiz", json={"action": "reveal"})
    view = student.get(f"/api/p/{student.code}").json()["activities"][0]
    assert view["question"]["correct"] == [0] and view["quiz"]["my_score"] > 500 and view["quiz"]["my_rank"] == 1
    teacher.post(f"/api/activities/{a['id']}/quiz", json={"action": "next"})
    teacher.post(f"/api/activities/{a['id']}/quiz", json={"action": "next"})
    t = teacher.get(f"/api/sessions/{session['id']}").json()["activities"][0]
    assert t["quiz"]["phase"] == "finished" and t["quiz"]["players"] == 1


# ---------- privacy ----------

def test_teacher_never_sees_participant_identifiers(teacher, session, student):
    a = teacher.post(f"/api/sessions/{session['id']}/activities", json={"kind": "ideas", "title": "I"}).json()
    p = poll(teacher, session)
    student.post(f"/api/p/{student.code}/a/{a['id']}/submit", json={"text": "Mehr Sport"})
    student.post(f"/api/p/{student.code}/a/{p['id']}/vote", json={"payload": {"choice": 0}})
    body = json.dumps(teacher.get(f"/api/sessions/{session['id']}").json())
    token = student.headers["X-Participant"]
    for forbidden in ("voter", token, "testclient", "ip", "user_agent"):
        assert f'"{forbidden}"' not in body and token not in body


def test_votes_unlinkable_across_activities(teacher, session, student):
    from classpulse.db import SessionLocal
    from classpulse.models import Response
    p1, p2 = poll(teacher, session), poll(teacher, session)
    for p in (p1, p2):
        student.post(f"/api/p/{student.code}/a/{p['id']}/vote", json={"payload": {"choice": 0}})
    with SessionLocal() as db:
        voters = {r.voter for r in db.query(Response).all()}
    assert len(voters) == 2  # same device, different pseudonym per activity
    assert student.headers["X-Participant"] not in voters


def test_participant_needs_token(session):
    with make_client() as c:
        assert c.get(f"/api/p/{session['code']}").status_code == 401


def test_delete_account_removes_everything(teacher, session, student):
    a = teacher.post(f"/api/sessions/{session['id']}/activities", json={"kind": "ideas", "title": "I"}).json()
    student.post(f"/api/p/{student.code}/a/{a['id']}/submit", json={"text": "Idee"})
    assert teacher.delete("/api/auth/me").status_code == 200
    from classpulse.db import SessionLocal
    from classpulse.models import ClassSession, Submission
    with SessionLocal() as db:
        assert db.query(ClassSession).count() == 0 and db.query(Submission).count() == 0


def test_cleanup_deletes_old_sessions(teacher, session):
    from datetime import timedelta

    from classpulse.db import SessionLocal
    from classpulse.main import cleanup
    from classpulse.models import ClassSession, now
    with SessionLocal() as db:
        cs = db.get(ClassSession, session["id"])
        cs.ended_at = cs.expires_at = now() - timedelta(days=400)
        db.commit()
    assert cleanup() == 1


# ---------- websockets ----------

def test_websocket_live_updates_and_participant_count(teacher, session, student):
    # one TestClient (= one event loop) for both sockets; the participant endpoints ignore the cookie
    a = poll(teacher, session)
    with teacher.websocket_connect(f"/ws/t/{session['id']}") as tws:
        assert tws.receive_json() == {"type": "participants", "count": 0}
        with teacher.websocket_connect(f"/ws/p/{student.code}") as sws:
            assert tws.receive_json() == {"type": "participants", "count": 1}
            teacher.post(f"/api/p/{student.code}/a/{a['id']}/vote", json={"payload": {"choice": 0}},
                         headers={"X-Participant": student.headers["X-Participant"]})
            assert tws.receive_json() == {"type": "changed", "activity": a["id"]}
            assert sws.receive_json() == {"type": "changed", "activity": a["id"]}
        # The TestClient runs each socket on its own event loop, so instead of waiting for the
        # cross-loop "count 0" push (racy in tests only) we check the hub directly.
        import time

        from classpulse.realtime import hub
        for _ in range(50):
            if hub.count(f"p:{session['id']}") == 0:
                break
            time.sleep(0.05)
        assert hub.count(f"p:{session['id']}") == 0


def test_teacher_websocket_requires_owner(session):
    import pytest
    from starlette.websockets import WebSocketDisconnect
    with make_client() as anon, pytest.raises(WebSocketDisconnect):
        with anon.websocket_connect(f"/ws/t/{session['id']}") as ws:
            ws.receive_json()
