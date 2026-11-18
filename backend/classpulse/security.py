import base64
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from .config import get_settings

# --- passwords (scrypt from the standard library, OWASP-recommended parameters) ---
_N, _R, _P = 2**15, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, maxmem=64 * 1024 * 1024, dklen=32)
    return f"scrypt${_N}${_R}${_P}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, dk = stored.split("$")
        got = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            maxmem=64 * 1024 * 1024,
            dklen=32,
        )
        return hmac.compare_digest(got, base64.b64decode(dk))
    except (ValueError, TypeError):
        return False


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def voter_hash(participant_token: str, activity_id: str) -> str:
    """Per-activity pseudonym: same device + same activity -> same value; nothing else links."""
    key = get_settings().secret_key.encode()
    return hmac.new(key, f"{activity_id}:{participant_token}".encode(), hashlib.sha256).hexdigest()


# No 0/O, 1/I/L -> easy to read from a projector, ~35 bits for 7 chars.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def new_session_code(length: int = 7) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


# --- rate limiting ---
class RateLimiter:
    """Sliding-window limiter kept in memory only (nothing persisted, keys are hashed).

    shortcut: per-process memory; with several workers use a shared store such as Redis.
    """

    def __init__(self):
        self.hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str, limit: int, window: float) -> bool:
        t = time.monotonic()
        q = self.hits[key]
        while q and q[0] <= t - window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(t)
        if len(self.hits) > 50_000:  # bound memory under attack
            self.hits.clear()
        return True

    def count(self, key: str, window: float) -> int:
        q = self.hits.get(key)
        if not q:
            return 0
        t = time.monotonic()
        while q and q[0] <= t - window:
            q.popleft()
        return len(q)

    def record(self, key: str):
        self.hits[key].append(time.monotonic())

    def reset(self):
        self.hits.clear()


limiter = RateLimiter()


def client_key(request: Request) -> str:
    # IP is only used transiently, hashed, in memory, for abuse protection - never stored.
    ip = request.client.host if request.client else "?"
    return sha256(get_settings().secret_key + ip)[:24]


def rate_limit(request: Request, bucket: str, limit: int, window: float, extra: str = "") -> None:
    if not limiter.check(f"{bucket}:{client_key(request)}:{extra}", limit, window):
        raise HTTPException(429, detail="rate_limited")
