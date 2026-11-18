"""Server-side content filter: normalisation + rules + optional AI second opinion.

Rejected texts are never stored or logged; only the reason code goes back to the student.
"""

import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass

import httpx

from ..config import get_settings
from .wordlists import ALLOWLIST, CATEGORIES, EDUCATIONAL_IN_QUESTIONS, LEVELS

log = logging.getLogger(__name__)

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
# Cyrillic/Greek look-alikes -> Latin
_HOMOGLYPHS = str.maketrans("аеорсухіјкмнтвАЕОРСУХІЈКМНТВοαειυκνρτχ", "aeopcyxijkmhtbaeopcyxijkmhtbоaeiuknptx")
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "9": "g",
                       "@": "a", "$": "s", "!": "i", "€": "e", "|": "i", "+": "t"})
_GERMAN = (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "ss"), ("ae", "a"), ("oe", "o"), ("ue", "u"))
_WORD = re.compile(r"[a-z0-9]+")
_URL = re.compile(
    r"(https?://|www\.|\b[a-z0-9-]{2,}\.(com|de|net|org|io|ly|me|info|biz|xyz|ru|tk|gg|co|at|ch|eu|app|link"
    r"|click|site|online|shop|top|live|tv)\b|\b(t\.me|wa\.me|bit\.ly|discord\.gg)/)",
    re.IGNORECASE,
)
_QUESTION_START = re.compile(
    r"^(was|wie|warum|wieso|weshalb|wer|wo|wann|welche[rsmn]?|kann|darf|ist|sind|what|why|how|who|where"
    r"|when|which|is|are|can|does|do)\b"
)


def _fold(text: str, leet: bool) -> str:
    t = text.translate(_ZERO_WIDTH).translate(_HOMOGLYPHS).lower()
    t = unicodedata.normalize("NFKC", t)
    for a, b in _GERMAN[:4]:
        t = t.replace(a, b)
    # strip remaining accents (é -> e)
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    if leet:
        t = t.translate(_LEET)
    for a, b in _GERMAN[4:]:
        t = t.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", t)  # fuuuuck -> fuck, scheisse -> scheise


def word_variants(text: str) -> list[list[str]]:
    """Token lists for several readings of the text to defeat obfuscation."""
    out = []
    # "f*ck", "sch#iße": masked letters are usually vowels
    texts = [text] + ([text.replace("*", v).replace("#", v) for v in "aeiou"] if re.search(r"\w[*#]", text) else [])
    for t, leet in ((t, leet) for t in texts for leet in (False, True)):
        folded = _fold(t, leet)
        tokens = _WORD.findall(folded)
        out.append(tokens)
        # "f u c k" / "f.u.c.k" (max_len 1) and "fu-ck" (max_len 3) -> join runs of short fragments
        for max_len in (1, 3):
            joined = _join_short(tokens, max_len)
            if joined != tokens:
                out.append(joined)
    return out


def _join_short(tokens: list[str], max_len: int) -> list[str]:
    joined, run = [], []
    for tok in [*tokens, None]:
        if tok is not None and len(tok) <= max_len:
            run.append(tok)
            continue
        joined.extend(["".join(run)] if len(run) >= 2 else run)
        run = []
        if tok is not None:
            joined.append(tok)
    return joined


def _norm_term(term: str) -> str:
    return " ".join(_WORD.findall(_fold(term, leet=False)))


def _compile():
    compiled = {}
    for name, cat in CATEGORIES.items():
        compiled[name] = {
            "level": cat["level"],
            "exact": {_norm_term(t) for t in cat["exact"]},
            "phrases": [_norm_term(t) for t in cat["phrases"]],
            "stems": [_norm_term(t) for t in cat["stems"]],
        }
    return compiled


_RULES = _compile()
_ALLOW = {_norm_term(w) for w in ALLOWLIST}
_EDU = {_norm_term(w) for w in EDUCATIONAL_IN_QUESTIONS}


@dataclass
class FilterResult:
    ok: bool
    reason: str = ""  # inappropriate | link | spam | too_long | empty | invalid | duplicate


OK = FilterResult(True)


def _is_question(text: str) -> bool:
    t = _fold(text, leet=False).strip()
    return text.strip().endswith("?") and bool(_QUESTION_START.match(t))


def _match_rules(variants, level: int, extra_block: set[str], allow: set[str], question: bool) -> bool:
    for tokens in variants:
        joined = " " + " ".join(tokens) + " "
        for tok in tokens:
            if tok in allow:
                continue
            for stem in extra_block:
                if tok.startswith(stem):
                    return True
            for cat in _RULES.values():
                if cat["level"] > level:
                    continue
                if tok in cat["exact"]:
                    if question and level < 3 and tok in _EDU:
                        continue
                    return True
                if any(tok.startswith(s) for s in cat["stems"]):
                    return True
        for cat in _RULES.values():
            if cat["level"] <= level and any(f" {p} " in joined for p in cat["phrases"]):
                return True
    return False


def _looks_like_spam(text: str, level: int) -> bool:
    letters = [c for c in text if c.isalpha()]
    if re.search(r"(.)\1{9,}", text):  # aaaaaaaaaa
        return True
    if re.search(r"(\b\w+\b)(\W+\1\b){4,}", text, re.IGNORECASE):  # same word 5x
        return True
    if len(text) >= 12 and len(set(text.lower())) <= 3:
        return True
    if level >= 3 and len(letters) >= 12 and sum(c.isupper() for c in letters) / len(letters) > 0.8:
        return True  # SHOUTING
    return False


def _invalid_chars(text: str) -> bool:
    if any(unicodedata.category(c) in ("Cc", "Cf", "Co", "Cs") and c not in "\n\t" for c in text):
        return True
    marks = sum(unicodedata.combining(c) > 0 for c in text)
    return marks > 10 and marks > len(text) * 0.3  # zalgo text


def check_text(
    text: str,
    level: str = "medium",
    blocked: list[str] | None = None,
    allowed: list[str] | None = None,
    max_len: int = 500,
) -> FilterResult:
    """Rule-based check. Fast, offline, no external service."""
    lvl = LEVELS.get(level, 2)
    stripped = text.strip()
    if not stripped:
        return FilterResult(False, "empty")
    if len(stripped) > max_len:
        return FilterResult(False, "too_long")
    if _invalid_chars(stripped):
        return FilterResult(False, "invalid")
    if lvl >= 2 and _URL.search(stripped):
        return FilterResult(False, "link")
    extra_block = {_norm_term(w) for w in (blocked or []) if _norm_term(w)}
    allow = _ALLOW | {_norm_term(w) for w in (allowed or [])}
    if _match_rules(word_variants(stripped), lvl, extra_block, allow, _is_question(stripped)):
        return FilterResult(False, "inappropriate")
    if _looks_like_spam(stripped, lvl):
        return FilterResult(False, "spam")
    return OK


_AI_PROMPT = (
    "You moderate anonymous messages written by school students (age 10-18) in a classroom app. "
    "Reply ONLY with JSON {\"allow\": true|false}. Block insults, bullying, hate, discrimination, threats, "
    "sexual content, glorified violence, extremism, spam or ads. Allow normal questions, opinions, song "
    "titles and harmless slang, including questions about sensitive school topics (history, biology)."
)


async def ai_check(text: str) -> FilterResult:
    """Optional second opinion from an OpenAI-compatible endpoint (e.g. local Ollama).

    Fails open to the rule-based result: an unreachable AI never blocks the class.
    """
    s = get_settings()
    if not (s.ai_filter_url and s.ai_filter_model):
        return OK
    headers = {"Authorization": f"Bearer {s.ai_filter_api_key}"} if s.ai_filter_api_key else {}
    body = {
        "model": s.ai_filter_model,
        "temperature": 0,
        "messages": [{"role": "system", "content": _AI_PROMPT}, {"role": "user", "content": text[:1000]}],
    }
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.post(s.ai_filter_url, json=body, headers=headers)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match and json.loads(match.group(0)).get("allow") is False:
                return FilterResult(False, "inappropriate")
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        log.warning("AI filter unavailable - using rule-based result only")
    return OK


class RecentMessages:
    """Blocks the same device from repeating the same text (in memory, hashed, short-lived)."""

    def __init__(self, window: float = 600):
        self.window = window
        self.seen: dict[str, float] = {}

    def is_repeat(self, key: str) -> bool:
        t = time.monotonic()
        if len(self.seen) > 20_000:
            self.seen = {k: v for k, v in self.seen.items() if v > t - self.window}
        if self.seen.get(key, 0) > t - self.window:
            return True
        self.seen[key] = t
        return False


recent = RecentMessages()


async def moderate(text: str, session, max_len: int = 500) -> FilterResult:
    res = check_text(text, session.filter_level, session.blocked_words, session.allowed_words, max_len)
    if res.ok:
        res = await ai_check(text)
    return res


def dedupe_key(text: str) -> str:
    return " ".join(_WORD.findall(_fold(text, leet=False)))[:200]
