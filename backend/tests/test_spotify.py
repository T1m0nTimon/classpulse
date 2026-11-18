"""Spotify integration against a mocked Spotify API (no network)."""

import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from classpulse import spotify

TRACK = {"id": "4uLU6hMCjMI75M1A2tKUQC", "uri": "spotify:track:4uLU6hMCjMI75M1A2tKUQC", "name": "Song A",
         "artists": [{"name": "Artist"}], "album": {"name": "Album", "images": [{"url": "https://i.scdn.co/big"},
                                                                              {"url": "https://i.scdn.co/small"}]},
         "external_urls": {"spotify": "https://open.spotify.com/track/x"}, "explicit": False}
EXPLICIT = {**TRACK, "id": "1111111111111111111111", "uri": "spotify:track:1111111111111111111111", "explicit": True}


@pytest.fixture
def fake_spotify():
    calls = []

    def handler(req: httpx.Request):
        calls.append((req.method, req.url.path, req.content))
        p = req.url.path
        if p == "/api/token":
            assert req.headers["authorization"].startswith("Basic ")
            return httpx.Response(200, json={"access_token": "AT", "refresh_token": "RT", "expires_in": 3600})
        assert req.headers["authorization"] == "Bearer AT"
        if p == "/v1/me":
            return httpx.Response(200, json={"id": "teacher1", "display_name": "Frau Lehrerin"})
        if p == "/v1/search":
            assert req.url.params["limit"] == "10" and req.url.params["type"] == "track"
            return httpx.Response(200, json={"tracks": {"items": [TRACK, EXPLICIT]}})
        if p.startswith("/v1/tracks/"):
            return httpx.Response(200, json=TRACK if p.endswith(TRACK["id"]) else EXPLICIT)
        if p == "/v1/me/playlists" and req.method == "POST":
            return httpx.Response(201, json={"id": "PL1", "external_urls": {"spotify": "https://open.spotify.com/playlist/PL1"}})
        if p == "/v1/playlists/PL1/items":
            return httpx.Response(200 if req.method == "DELETE" else 201, json={"snapshot_id": "s"})
        return httpx.Response(404)

    spotify.transport = httpx.MockTransport(handler)
    yield calls
    spotify.transport = None


def connect(teacher):
    r = teacher.get("/api/spotify/login", follow_redirects=False)
    assert r.status_code == 302
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert q["redirect_uri"][0] == "http://testserver/api/spotify/callback"
    assert "client_secret" not in r.headers["location"] and "csecret" not in r.headers["location"]
    bad = teacher.get("/api/spotify/callback", params={"code": "c", "state": "wrong"}, follow_redirects=False)
    assert bad.headers["location"] == "/?spotify=error"
    ok = teacher.get("/api/spotify/callback", params={"code": "c", "state": q["state"][0]}, follow_redirects=False)
    assert ok.headers["location"] == "/?spotify=connected"


def test_oauth_connect_and_status(teacher, fake_spotify):
    assert teacher.get("/api/spotify/status").json()["connected"] is False
    connect(teacher)
    st = teacher.get("/api/spotify/status").json()
    assert st == {"enabled": True, "connected": True, "display_name": "Frau Lehrerin"}
    teacher.post("/api/spotify/disconnect")
    assert teacher.get("/api/spotify/status").json()["connected"] is False


def test_music_queue_with_playlist_sync(teacher, session, student, fake_spotify):
    connect(teacher)
    a = teacher.post(f"/api/sessions/{session['id']}/activities", json={"kind": "music", "title": "Party"}).json()
    assert a["playlist_url"].endswith("PL1") and a["moderation"] is True
    base = f"/api/p/{student.code}/a/{a['id']}"
    results = student.get(base + "/search", params={"q": "song"}).json()
    assert [t["id"] for t in results] == [TRACK["id"]]  # explicit filtered out
    assert results[0]["image"] == "https://i.scdn.co/small"
    assert student.post(base + "/submit", json={"track_id": EXPLICIT["id"]}).json()["detail"] == "filter:explicit"
    assert student.post(base + "/submit", json={"track_id": "../../me"}).status_code == 502
    assert student.post(base + "/submit", json={"track_id": TRACK["id"]}).json()["status"] == "pending"
    from conftest import new_student
    with new_student(student.code) as s2:
        assert s2.post(base + "/submit", json={"track_id": TRACK["id"]}).json()["merged"] is True  # duplicate
    item = teacher.get(f"/api/sessions/{session['id']}").json()["activities"][0]["items"][0]
    assert item["votes"] == 2 and item["song"]["name"] == "Song A"
    teacher.patch(f"/api/submissions/{item['id']}", json={"status": "approved"})
    added = [c for c in fake_spotify if c[0] == "POST" and c[1] == "/v1/playlists/PL1/items"]
    assert json.loads(added[0][2]) == {"uris": [TRACK["uri"]]}
    teacher.delete(f"/api/submissions/{item['id']}")
    removed = [c for c in fake_spotify if c[0] == "DELETE"]
    assert json.loads(removed[0][2]) == {"items": [{"uri": TRACK["uri"]}]}


def test_music_without_spotify_uses_text_wishes(teacher, session, student):
    a = teacher.post(f"/api/sessions/{session['id']}/activities", json={"kind": "music", "title": "M"}).json()
    assert a["sync_spotify"] is False
    base = f"/api/p/{student.code}/a/{a['id']}"
    assert student.get(base + "/search", params={"q": "x"}).json()["detail"] == "spotify_not_connected"
    assert student.post(base + "/submit", json={"text": "Bohemian Rhapsody – Queen"}).status_code == 200
    assert student.post(base + "/submit", json={"text": "fick dich"}).status_code == 422


def test_spotify_not_configured(teacher, monkeypatch):
    from classpulse.config import get_settings
    monkeypatch.setattr(get_settings(), "spotify_client_id", "")
    assert teacher.get("/api/spotify/login").json()["detail"] == "spotify_not_configured"
    assert teacher.get("/api/config").json()["spotify_enabled"] is False
