"""Rule lists for the content filter (German + English; add more languages by appending terms).

Terms can be written naturally - they are run through the same normalisation as user text at
import time (lowercase, umlauts folded, leetspeak folded, repeated letters collapsed).

Each category has a minimum filter level at which it is enforced:
  low (1)    -> severe only: threats, slurs, extremism, sexual, violence
  medium (2) -> + insults, spam/ads (+ links, handled in engine.py)
  high (3)   -> + mild profanity and rude words

- `exact`   must match a whole word
- `phrases` must match a sequence of whole words
- `stems`   also match at the start of a word; catches compounds ("hurensohnmäßig"). Only used where
            false positives are unlikely; ALLOWLIST rescues known harmless words.
Teachers can add blocked/allowed words per session on top of these lists.
"""

LEVELS = {"low": 1, "medium": 2, "high": 3}

CATEGORIES: dict[str, dict] = {
    "threat": {
        "level": 1,
        "exact": ["kys"],
        "phrases": [
            "ich bring dich um", "ich bringe dich um", "ich töte dich", "ich mach dich kalt",
            "ich stech dich ab", "ich steche dich ab", "du bist tot", "ich weiß wo du wohnst",
            "ich weiss wo du wohnst", "i will kill you", "ill kill you", "i'll kill you",
            "im going to kill you", "gonna kill you", "i know where you live", "kill yourself",
            "bring dich um", "erschieß dich", "amoklauf", "school shooting", "bombe in der schule",
            "bomb the school", "shoot up the school", "ich spreng die schule", "ich jag die schule",
            "abstechen", "ich schlag dich tot", "ich schlage dich tot",
        ],
        "stems": ["schulshooting", "schulamok"],
    },
    "slur": {
        "level": 1,
        "exact": ["nigga", "kanake", "zigeuner", "spast", "tranny", "chink", "kike", "faggot", "fag",
                  "retard", "schwuchtel", "neger", "polacke", "kanacke", "mongo"],
        "phrases": [],
        "stems": ["nigger", "nigga", "kanack", "kanak", "schwuchtel", "spasti", "faggot", "negerkuss"],
    },
    "extremism": {
        "level": 1,
        "exact": ["1488", "siegheil", "heilhitler"],
        "phrases": ["heil hitler", "sieg heil", "white power", "juden raus", "ausländer raus",
                    "gas the jews", "white pride", "tod den juden", "rassenkrieg", "race war"],
        "stems": ["judensau", "nazischwein", "kanakenraus"],
    },
    "sexual": {
        "level": 1,
        "exact": ["porn", "porno", "nudes", "titten", "tits", "boobs", "pussy", "dick", "cock",
                  "blowjob", "fick", "ficken", "fickt", "gefickt", "fuck", "fucking", "fucked", "cum",
                  "wichsen", "horny", "milf", "onlyfans", "xxx", "hentai", "dildo", "muschi", "pimmel",
                  "schwanz lutschen", "sex", "penis", "vagina", "nackt", "orgasmus", "orgasm", "anal"],
        "phrases": ["send nudes", "schick nudes", "zeig titten", "lutsch meinen"],
        "stems": ["porno", "fick", "fuck", "titten", "blowjob", "pornhub", "xvideos", "wichs"],
    },
    "violence": {
        "level": 1,
        "exact": ["vergewaltigen", "rape", "massaker"],
        "phrases": ["alle umbringen", "kill them all", "alle abstechen", "alle erschießen"],
        "stems": ["vergewaltig"],
    },
    "insult": {
        "level": 2,
        "exact": ["arschloch", "arsch", "idiot", "idioten", "depp", "trottel", "missgeburt",
                  "hurensohn", "hure", "nutte", "schlampe", "fotze", "bitch", "bastard", "asshole",
                  "dumbass", "loser", "behindert", "huso", "wixxer", "wichser", "motherfucker", "slut",
                  "whore", "cunt", "twat", "wanker", "dummkopf", "vollidiot", "penner", "spacko",
                  "fettsack", "fettsau", "hässlich", "ugly", "fatass", "moron", "pisser", "kackbratze",
                  "drecksau", "missgeburt", "opfa", "lowkey hässlich"],
        "phrases": ["halt die fresse", "halts maul", "halt dein maul", "shut up", "fresse halten",
                    "du bist dumm", "ihr seid dumm", "you suck", "verpiss dich", "fick dich", "fuck you",
                    "go to hell", "geh sterben", "deine mutter", "deine mudda", "your mom", "yo mama"],
        "stems": ["hurensohn", "arschloch", "missgeburt", "fotze", "schlampe", "motherfuck", "wichser",
                  "vollidiot", "drecks"],
    },
    "spam": {
        "level": 2,
        "exact": ["rabattcode", "gewinnspiel", "casino"],
        "phrases": ["folgt mir", "follow me", "check out my", "abonniert meinen", "abonniert mich",
                    "link in bio", "free money", "gratis geld", "click here", "klick hier", "dm me",
                    "schreib mir auf", "add me on", "adde mich"],
        "stems": [],
    },
    "profanity": {
        "level": 3,
        "exact": ["scheiße", "scheisse", "shit", "kacke", "damn", "crap", "verdammt", "wtf",
                  "bullshit", "piss", "kack", "dumm", "doof", "blöd", "stupid", "geil", "fresse"],
        "phrases": [],
        "stems": ["scheiß", "scheiss", "bullshit"],
    },
}

# Harmless words that start with a stem above (Scunthorpe problem).
ALLOWLIST = {
    "nigeria", "nigerianer", "nigerianisch", "kanada", "kanadier", "kanal", "kanarienvogel",
    "kanaren", "schuhwichse", "dreckspatz", "fickfacker", "titicacasee",
}

# Educational words: allowed inside a genuine question ("Was ist Sex?", "What is anal fixation?")
# unless the level is "high". Only these exact words are relaxed, never threats/slurs/extremism.
EDUCATIONAL_IN_QUESTIONS = {"sex", "penis", "vagina", "nackt", "orgasmus", "orgasm", "anal", "porno",
                            "porn", "vergewaltigen", "massaker", "rape", "behindert", "dumm", "doof"}
