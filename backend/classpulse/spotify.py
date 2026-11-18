"""Spotify Web API integration (Authorization Code flow, server-side; secrets never reach the browser).

Uses the endpoints valid after Spotify's February 2026 Web API changes:
  GET  /v1/search (limit <= 10)          GET /v1/tracks/{id}       GET /v1/me
  POST /v1/me/playlists                  POST/DELETE /v1/playlists/{id}/items
Development-mode apps: the app owner needs Spotify Premium and only allow-listed users can connect.
"""

import base64
import re
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .auth import current_teacher
from .config import get_settings
from .db import get_db
from .models import SpotifyAccount, Teacher, now

router = APIRouter(prefix="/api/spotify", tags=["spotify"])
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"  # noqa: S105 - URL, not a secret
API = "https://api.spotify.com/v1"
SCOPES = "playlist-modify-private playlist-modify-public"
TRACK_ID = re.compile(r"^[A-Za-z0-9]{22}$")

# Overridable in tests.
transport: httpx.BaseTransport | None = None


class SpotifyError(Exception):
    pass


def _client() -> httpx.Client:
    return httpx.Client(timeout=10, transport=transport)


def redirect_uri(request: Request) -> str:
    s = get_settings()
    base = s.public_url.rstrip("/") or str(request.base_url).rstrip("/")
    # Spotify forbids "localhost" redirect URIs but allows the loopback IP.
    base = base.replace("://localhost", "://127.0.0.1")
    return f"{base}/api/spotify/callback"


def _basic() -> str:
    s = get_settings()
    return "Basic " + base64.b64encode(f"{s.spotify_client_id}:{s.spotify_client_secret}".encode()).decode()


def _require_enabled():
    if not get_settings().spotify_enabled:
        raise HTTPException(400, "spotify_not_configured")


@router.get("/status")
def status(teacher: Teacher = Depends(current_teacher)):
    acc = teacher.spotify
    return {"enabled": get_settings().spotify_enabled, "connected": bool(acc),
            "display_name": acc.display_name if acc else None}


@router.get("/login")
def login(request: Request, teacher: Teacher = Depends(current_teacher)):
    _require_enabled()
    state = secrets.token_urlsafe(24)
    url = AUTH_URL + "?" + urlencode({
        "client_id": get_settings().spotify_client_id, "response_type": "code",
        "redirect_uri": redirect_uri(request), "scope": SCOPES, "state": state,
    })
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie("cp_sp_state", state, max_age=600, httponly=True,
                    secure=get_settings().secure_cookies, samesite="lax", path="/api/spotify")
    return resp


@router.get("/callback")
def callback(request: Request, code: str = "", state: str = "", error: str = "",
             cp_sp_state: str | None = Cookie(default=None),
             teacher: Teacher = Depends(current_teacher), db: Session = Depends(get_db)):
    _require_enabled()
    target = "/?spotify="
    if error or not code or not cp_sp_state or not secrets.compare_digest(state, cp_sp_state):
        return RedirectResponse(target + "error", status_code=302)
    try:
        with _client() as c:
            r = c.post(TOKEN_URL, headers={"Authorization": _basic()}, data={
                "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri(request)})
            r.raise_for_status()
            tok = r.json()
            me = c.get(f"{API}/me", headers={"Authorization": f"Bearer {tok['access_token']}"})
            me.raise_for_status()
            profile = me.json()
    except (httpx.HTTPError, KeyError):
        return RedirectResponse(target + "error", status_code=302)
    acc = teacher.spotify or SpotifyAccount(teacher_id=teacher.id)
    acc.access_token = tok["access_token"]
    acc.refresh_token = tok.get("refresh_token", acc.refresh_token if teacher.spotify else "")
    acc.expires_at = now() + timedelta(seconds=int(tok.get("expires_in", 3600)) - 60)
    acc.spotify_user_id = profile.get("id", "")
    acc.display_name = profile.get("display_name") or profile.get("id", "")
    db.add(acc)
    db.commit()
    resp = RedirectResponse(target + "connected", status_code=302)
    resp.delete_cookie("cp_sp_state", path="/api/spotify")
    return resp


@router.post("/disconnect")
def disconnect(teacher: Teacher = Depends(current_teacher), db: Session = Depends(get_db)):
    if teacher.spotify:
        db.delete(teacher.spotify)
        db.commit()
    return {"ok": True}


# ---------- API calls on behalf of a teacher ----------

def _token(db: Session, acc: SpotifyAccount) -> str:
    if acc.expires_at > now():
        return acc.access_token
    with _client() as c:
        r = c.post(TOKEN_URL, headers={"Authorization": _basic()},
                   data={"grant_type": "refresh_token", "refresh_token": acc.refresh_token})
    if r.status_code != 200:
        raise SpotifyError("refresh_failed")
    tok = r.json()
    acc.access_token = tok["access_token"]
    acc.refresh_token = tok.get("refresh_token") or acc.refresh_token  # may or may not rotate
    acc.expires_at = now() + timedelta(seconds=int(tok.get("expires_in", 3600)) - 60)
    db.commit()
    return acc.access_token


def _call(db: Session, acc: SpotifyAccount, method: str, path: str, **kw) -> dict:
    try:
        with _client() as c:
            r = c.request(method, API + path, headers={"Authorization": f"Bearer {_token(db, acc)}"}, **kw)
    except httpx.HTTPError as e:
        raise SpotifyError("network") from e
    if r.status_code == 429:
        raise SpotifyError("rate_limited")
    if r.status_code >= 400:
        raise SpotifyError(f"http_{r.status_code}")
    return r.json() if r.content else {}


def track_dict(t: dict) -> dict:
    images = (t.get("album") or {}).get("images") or []
    return {
        "id": t["id"], "uri": t.get("uri", f"spotify:track:{t['id']}"), "name": t.get("name", "")[:200],
        "artists": ", ".join(a.get("name", "") for a in t.get("artists", []))[:200],
        "album": (t.get("album") or {}).get("name", "")[:200],
        # Spotify returns 640/300/64px, largest first: take the 300px one
        "image": images[min(1, len(images) - 1)]["url"] if images else None,
        "url": (t.get("external_urls") or {}).get("spotify"),
        "explicit": bool(t.get("explicit")),
    }


def search(db: Session, acc: SpotifyAccount, q: str, allow_explicit: bool) -> list[dict]:
    data = _call(db, acc, "GET", "/search", params={"q": q[:100], "type": "track", "limit": 10})
    tracks = [track_dict(t) for t in (data.get("tracks") or {}).get("items", []) if t]
    return [t for t in tracks if allow_explicit or not t["explicit"]]


def get_track(db: Session, acc: SpotifyAccount, track_id: str) -> dict:
    if not TRACK_ID.match(track_id):
        raise SpotifyError("invalid_track")
    return track_dict(_call(db, acc, "GET", f"/tracks/{track_id}"))


def create_playlist(db: Session, acc: SpotifyAccount, name: str) -> dict:
    data = _call(db, acc, "POST", "/me/playlists", json={
        "name": name[:100], "public": False, "description": "Created by ClassPulse"})
    return {"id": data["id"], "url": (data.get("external_urls") or {}).get("spotify")}


def add_items(db: Session, acc: SpotifyAccount, playlist_id: str, uris: list[str]):
    _call(db, acc, "POST", f"/playlists/{playlist_id}/items", json={"uris": uris[:100]})


def remove_items(db: Session, acc: SpotifyAccount, playlist_id: str, uris: list[str]):
    _call(db, acc, "DELETE", f"/playlists/{playlist_id}/items",
          json={"items": [{"uri": u} for u in uris[:100]]})
