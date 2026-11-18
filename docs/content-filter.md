# Content filter

Every free-text input (questions, ideas, song wishes, free-text poll answers) is checked **on the server** before it is stored. Rejected texts are not stored or logged; the student sees a friendly message.

## Pipeline

1. **Basic checks** — empty, too long, control characters, "Zalgo" text.
2. **Links** (from level *normal*) — URLs, domains, `t.me`, `discord.gg`, …
3. **Normalisation** — lowercase, Unicode NFKC, accents and umlauts folded (`ä→a`, `ae→a`, `ß→ss`), Cyrillic/Greek look-alikes (`і`, `о`) mapped to Latin, leetspeak (`3→e`, `1→i`, `@→a`, `$→s`), masked letters (`f*ck`), repeated letters collapsed (`fuuuck`), and letters split by spaces/dots/dashes joined again (`h.u.r.e.n.s.o.h.n`, `fu-ck`).
4. **Rule lists** (`backend/classpulse/filter/wordlists.py`, German + English) — whole words, phrases and word stems (catches compounds like "hurensohnmäßig"), with an allow-list against false positives (e.g. *Analyse*, *Nigeria*, *Cocktail*, *Kanal*).
5. **Context** — selected educational words ("Was ist Sex?") are allowed inside genuine questions below the strict level. Threats, slurs and extremism are never relaxed.
6. **Spam heuristics** — repeated characters/words, low character variety, ALL-CAPS shouting (strict level), and the same device repeating the same text within 10 minutes.
7. **Optional AI check** — only if configured and only for texts that passed the rules.

Rate limits additionally stop automated spam.

## Levels (per session, ⚙︎ settings)

| Level | Blocks |
|---|---|
| Relaxed | threats, hate/slurs, sexual content, glorified violence, extremism |
| Normal (default) | + insults/bullying, ads/self-promotion, links |
| Strict | + swear words, rude words, shouting |

Teachers can add **blocked words** (also block compounds starting with the word) and **allowed words** (if something harmless is blocked) per session.

## Optional AI moderation (free with Ollama)

Any OpenAI-compatible chat completion endpoint works:

```env
# local and free
AI_FILTER_URL=http://localhost:11434/v1/chat/completions
AI_FILTER_MODEL=llama3.2
# or a hosted provider
AI_FILTER_URL=https://api.example.com/v1/chat/completions
AI_FILTER_MODEL=some-model
AI_FILTER_API_KEY=...
```

If the endpoint is slow or unavailable, ClassPulse falls back to the rule result after 6 seconds — a broken AI never blocks a lesson. Note the privacy implication of sending texts to an external provider (see privacy.md).

## Honest limits

No filter is perfect. New slang, creative spelling or context-dependent bullying can slip through; rarely, a harmless word may be blocked. That's why questions and songs default to **teacher approval**, and teachers can reject or delete anything.
