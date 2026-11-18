import pytest

from classpulse.filter.engine import check_text


@pytest.mark.parametrize("text", [
    "Wann schreiben wir die Arbeit?", "Können wir mehr Gruppenarbeit machen?", "Analyse des Gedichts",
    "Nigeria liegt in Afrika", "Ein Cocktail aus Obst", "Classic Rock", "Dreck sammeln im Park",
    "Ausflug nach Berlin!", "Was ist Sex?", "What is the capital of Canada?", "Kanal 5", "Mathe ist cool 😎",
    "Wie funktioniert die Fotosynthese?", "Die Schuhwichse ist alle",
])
def test_harmless_texts_pass(text):
    assert check_text(text, "medium").ok, text


@pytest.mark.parametrize("text", [
    "Du Hurensohn", "du bist ein h.u.r.e.n.s.o.h.n", "f u c k", "fuuuuuck", "fu-ck you", "F*CK", "ARSCHLOCH",
    "Hässlich", "haesslich", "ich bring dich um", "Ich bringe dich um!!", "heil hitler", "h3il h1tler",
    "Sieg Heil", "send nudes", "Du Missgeburt", "halt die fresse", "schwuchtel", "Spast",
    "hurensohnmäßig", "Ich weiß wo du wohnst", "fіck dich",  # Cyrillic і
])
def test_bad_texts_blocked(text):
    res = check_text(text, "medium")
    assert not res.ok and res.reason == "inappropriate", text


def test_links_blocked_from_medium():
    assert check_text("schau mal www.example.com", "medium").reason == "link"
    assert check_text("https://evil.ru/x", "medium").reason == "link"
    assert check_text("discord.gg/abc", "high").reason == "link"
    assert check_text("schau mal www.example.com", "low").ok


def test_levels():
    assert check_text("Das ist Scheiße", "medium").ok
    assert not check_text("Das ist Scheiße", "high").ok
    assert check_text("Du Idiot", "low").ok
    assert not check_text("Du Idiot", "medium").ok
    assert not check_text("ich bring dich um", "low").ok


def test_educational_question_only_relaxed_below_high():
    assert check_text("Was ist Sex?", "medium").ok
    assert not check_text("Was ist Sex?", "high").ok
    assert not check_text("sex", "medium").ok


def test_spam_and_invalid():
    assert check_text("aaaaaaaaaaaaaaa", "medium").reason == "spam"
    assert check_text("kauf kauf kauf kauf kauf kauf", "medium").reason == "spam"
    assert check_text("folgt mir auf insta", "medium").reason == "inappropriate"
    assert check_text("   ", "medium").reason == "empty"
    assert check_text("x" * 600, "medium").reason == "too_long"
    assert check_text("hi\x00there", "medium").reason == "invalid"
    assert check_text("Z̷̢̛̖a̴̡̛l̵̢̛g̸̢̛o̵̡̕ ̶̢̛t̵̡̛ȩ̷̛x̵̡̛t̵̢̛", "medium").reason == "invalid"
    assert check_text("DAS IST SO LANGWEILIG HEUTE", "high").reason == "spam"


def test_teacher_custom_words():
    assert not check_text("Das ist ein Banane", "medium", blocked=["banane"]).ok
    assert not check_text("Bananenbrot", "medium", blocked=["banane"]).ok
    assert check_text("Du Idiot", "medium", allowed=["idiot"]).ok


def test_repeat_detection_right_after_boot(monkeypatch):
    # time.monotonic() starts near 0 on a freshly booted machine (e.g. Raspberry Pi, CI runner)
    from classpulse.filter import engine
    monkeypatch.setattr(engine.time, "monotonic", lambda: 5.0)
    r = engine.RecentMessages()
    assert r.is_repeat("k") is False and r.is_repeat("k") is True
