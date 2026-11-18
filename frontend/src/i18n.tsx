// Tiny i18n: add a language by adding one more object with the same keys.
import { createContext, useContext, useState, type ReactNode } from "react";
import { store } from "./api";

const de = {
  appName: "ClassPulse",
  greetMorning: "Guten Morgen!", greetDay: "Hallo!", greetEvening: "Guten Abend!",
  homeQuestion: "Was möchtest du heute mit deiner Klasse machen?",
  newSession: "Neue Sitzung erstellen",
  startPoll: "Abstimmung starten", startQuestions: "Fragerunde starten", startMusic: "Musikwünsche starten",
  startIdeas: "Ideensammlung starten", startQuiz: "Quiz erstellen",
  recentSessions: "Deine letzten Sitzungen", noSessions: "Noch keine Sitzungen – leg einfach los!",
  open: "Öffnen", back: "Zurück", cancel: "Abbrechen", save: "Speichern", delete: "Löschen", close: "Schließen",
  login: "Anmelden", register: "Konto erstellen", logout: "Abmelden", email: "E-Mail", password: "Passwort",
  name: "Dein Name (optional)", haveAccount: "Ich habe schon ein Konto", noAccount: "Ich bin neu hier",
  passwordHint: "Mindestens 8 Zeichen",
  tagline: "Abstimmungen, Fragen, Ideen und Musik – anonym und in 30 Sekunden startklar.",
  forStudents: "Schüler? Hier mit Code teilnehmen",
  // session
  live: "Läuft", paused: "Pausiert", ended: "Beendet",
  pause: "Pausieren", resume: "Fortsetzen", end: "Beenden", reopen: "Wieder öffnen",
  joinHow: "Scannen oder Code eingeben", code: "Code", participants: "Teilnehmer", link: "Link",
  copy: "Kopieren", copied: "Kopiert!", projector: "Beamer-Ansicht", present: "Präsentieren",
  addActivity: "Aktivität hinzufügen", noActivities: "Füge oben eine Aktivität hinzu – die Klasse sieht sie sofort.",
  settings: "Einstellungen", deleteSession: "Sitzung löschen", confirmDelete: "Wirklich löschen? Alle Antworten gehen verloren.",
  localhostWarn: "Handys können „localhost“ nicht öffnen. Öffne ClassPulse über diese Adresse, damit der QR-Code funktioniert:",
  // activity kinds
  poll: "Abstimmung", questions: "Fragerunde", ideas: "Ideensammlung", music: "Musikwünsche", quiz: "Quiz",
  single: "Eine Antwort", multi: "Mehrere Antworten", yesno: "Ja / Nein", scale: "Skala 1–10", text: "Freitext", ranking: "Rangfolge",
  yes: "Ja", no: "Nein",
  question: "Frage", yourQuestion: "Deine Frage an die Klasse", options: "Antworten", addOption: "Antwort hinzufügen",
  option: "Antwort", randomQuestion: "Zufallsfrage", showResults: "Ergebnisse für die Klasse",
  resultsLive: "Sofort zeigen", resultsAfter: "Erst nach Ende",
  start: "Starten", approvalOn: "Mit Freigabe", approvalOff: "Ohne Freigabe", topic: "Thema (optional)", moderation: "Erst nach meiner Freigabe sichtbar",
  explicit: "Songs mit „Explicit“-Kennzeichnung erlauben", syncSpotify: "Mit Spotify-Playlist synchronisieren",
  closeActivity: "Schließen", openActivity: "Öffnen", reset: "Zurücksetzen", confirmReset: "Alle Antworten dieser Aktivität löschen?",
  votes: "Stimmen", vote: "Stimme", average: "Durchschnitt", points: "Punkte", noVotesYet: "Noch keine Antworten",
  pending: "Wartet", approved: "Sichtbar", rejected: "Abgelehnt", done: "Erledigt",
  approve: "Freigeben", reject: "Ablehnen", markDone: "Erledigt", answer: "Antworten", answerPlaceholder: "Antwort für die Klasse…",
  sortTop: "Beliebteste", sortNew: "Neueste", waitingApproval: "warten auf Freigabe", nothingYet: "Noch nichts eingegangen",
  openPlaylist: "Playlist in Spotify öffnen", inPlaylist: "In Playlist", spotifyError: "Spotify-Fehler – Song wurde nicht synchronisiert. Ist Spotify noch verbunden?",
  // quiz
  quizTitle: "Titel des Quiz", addQuestion: "Frage hinzufügen", seconds: "Sekunden", correct: "richtig",
  markCorrect: "Tippe auf den Kreis, um die richtige Antwort zu markieren", quizStart: "Erste Frage zeigen",
  quizNext: "Nächste Frage", quizReveal: "Auflösen", quizFinish: "Quiz beenden", quizRestart: "Neu starten",
  quizWaiting: "Gleich geht's los!", quizFinished: "Quiz beendet", answers: "Antworten", players: "Mitspieler",
  topScores: "Bestenliste (anonym)", yourScore: "Deine Punkte", yourRank: "Dein Platz", of: "von",
  answered: "Antwort gesendet!", timeLeft: "Sekunden übrig", rightAnswer: "Richtig!", wrongAnswer: "Leider falsch",
  questionN: "Frage {n} von {m}",
  // settings
  filter: "Inhaltsfilter", filterLow: "Locker", filterMedium: "Normal", filterHigh: "Streng",
  filterHelpLow: "Blockiert nur Schweres: Drohungen, Hass, Sexuelles, Extremismus.",
  filterHelpMedium: "Zusätzlich Beleidigungen, Werbung und Links. Empfohlen.",
  filterHelpHigh: "Zusätzlich Schimpfwörter und GROSSBUCHSTABEN-Geschrei.",
  blockedWords: "Zusätzlich blockierte Wörter", allowedWords: "Erlaubte Wörter (falls etwas zu Unrecht blockiert wird)",
  wordsHint: "Mit Komma trennen", language: "Sprache",
  spotify: "Spotify", spotifyConnect: "Mit Spotify verbinden", spotifyConnected: "Verbunden als", spotifyDisconnect: "Trennen",
  spotifyNotConfigured: "Spotify ist auf diesem Server nicht eingerichtet. Musikwünsche funktionieren trotzdem – als Text.",
  spotifyHelp: "Damit landen freigegebene Songs automatisch in einer Playlist.",
  account: "Konto", deleteAccount: "Konto und alle Daten löschen", confirmDeleteAccount: "Konto und alle Sitzungen endgültig löschen?",
  privacyNote: "Schüler bleiben anonym: keine Namen, keine Konten, keine IP-Adressen in der Datenbank.",
  // student
  joinTitle: "Teilnehmen", enterCode: "Code von der Tafel eingeben", join: "Los geht's",
  anonymous: "Du bist anonym. Niemand – auch nicht die Lehrkraft – sieht, was von dir kommt.",
  sessionPaused: "Kurze Pause – gleich geht's weiter.", sessionEnded: "Diese Sitzung ist beendet. Danke fürs Mitmachen!",
  noActivitiesStudent: "Gleich geht's los – warte auf deine Lehrkraft.",
  send: "Senden", sent: "Gesendet!", sentPending: "Gesendet! Erscheint nach Freigabe.", merged: "Gibt es schon – deine Stimme wurde gezählt!",
  thanksVote: "Danke für deine Stimme!", resultsLater: "Die Ergebnisse gibt es am Ende.", closed: "Geschlossen",
  askPlaceholder: "Deine Frage…", ideaPlaceholder: "Deine Idee…", songPlaceholder: "Song suchen…", songTextPlaceholder: "Titel – Künstler",
  textAnswerPlaceholder: "Deine Antwort…", search: "Suchen", suggest: "Vorschlagen", rankHint: "Tippe die Antworten in deiner Reihenfolge an",
  resetRank: "Neu ordnen", submitVote: "Abstimmen", reconnecting: "Verbindung wird wiederhergestellt…",
  // errors
  "err.network": "Keine Verbindung. Bitte prüfe dein Internet.",
  "err.session_not_found": "Diesen Code gibt es nicht. Bitte noch mal prüfen.",
  "err.session_ended": "Diese Sitzung ist beendet.", "err.session_paused": "Die Sitzung ist gerade pausiert.",
  "err.activity_closed": "Diese Aktivität ist geschlossen.", "err.already_voted": "Du hast schon abgestimmt.",
  "err.already_answered": "Du hast schon geantwortet.", "err.question_closed": "Diese Frage ist schon vorbei.", "err.time_up": "Die Zeit ist um.",
  "err.rate_limited": "Etwas langsamer bitte – versuch es gleich noch mal.",
  "err.filter:inappropriate": "Das können wir so nicht senden. Bitte formuliere es freundlich und respektvoll.",
  "err.filter:link": "Links sind hier nicht erlaubt.", "err.filter:spam": "Das sieht nach Spam aus. Bitte schreib einen normalen Satz.",
  "err.filter:too_long": "Das ist zu lang. Bitte kürzer fassen.", "err.filter:empty": "Bitte schreib etwas.",
  "err.filter:invalid": "Der Text enthält ungültige Zeichen.", "err.filter:duplicate": "Das hast du gerade schon gesendet.",
  "err.filter:explicit": "Dieser Song ist als „Explicit“ markiert und hier nicht erlaubt.",
  "err.spotify_not_connected": "Spotify ist nicht verbunden.", "err.spotify_unavailable": "Spotify antwortet gerade nicht. Versuch es gleich noch mal.",
  "err.spotify_not_configured": "Spotify ist auf diesem Server nicht eingerichtet.",
  "err.wrong_credentials": "E-Mail oder Passwort stimmt nicht.", "err.email_taken": "Mit dieser E-Mail gibt es schon ein Konto.",
  "err.registration_closed": "Neue Konten sind auf diesem Server deaktiviert.",
  "err.need_two_options": "Bitte gib mindestens zwei Antworten ein.", "err.need_questions": "Bitte füge mindestens eine Frage hinzu.",
  "err.invalid": "Bitte prüfe deine Eingaben.", "err.error": "Da ist etwas schiefgelaufen. Bitte versuch es noch mal.",
  spotifyConnectedMsg: "Spotify ist jetzt verbunden.", spotifyErrorMsg: "Spotify-Verbindung hat nicht geklappt. Bitte noch mal versuchen.",
  randomQuestions: [
    "Wie fühlst du dich heute (1 = müde, 10 = topfit)?", "Was war heute das Interessanteste?", "Wie gut hast du das Thema verstanden?",
    "Welche Superkraft hättest du gern?", "Was sollten wir als Nächstes wiederholen?", "Wie war das Tempo heute?",
    "Wohin sollte unser nächster Ausflug gehen?", "Was hat dir diese Woche Freude gemacht?",
  ],
};

type Dict = typeof de;

const en: Dict = {
  appName: "ClassPulse",
  greetMorning: "Good morning!", greetDay: "Hello!", greetEvening: "Good evening!",
  homeQuestion: "What would you like to do with your class today?",
  newSession: "Create new session",
  startPoll: "Start a poll", startQuestions: "Start a Q&A", startMusic: "Start music wishes",
  startIdeas: "Collect ideas", startQuiz: "Create a quiz",
  recentSessions: "Your recent sessions", noSessions: "No sessions yet – just get started!",
  open: "Open", back: "Back", cancel: "Cancel", save: "Save", delete: "Delete", close: "Close",
  login: "Sign in", register: "Create account", logout: "Sign out", email: "Email", password: "Password",
  name: "Your name (optional)", haveAccount: "I already have an account", noAccount: "I'm new here",
  passwordHint: "At least 8 characters",
  tagline: "Polls, questions, ideas and music – anonymous and ready in 30 seconds.",
  forStudents: "Student? Join with a code",
  live: "Live", paused: "Paused", ended: "Ended",
  pause: "Pause", resume: "Resume", end: "End", reopen: "Reopen",
  joinHow: "Scan or enter the code", code: "Code", participants: "Participants", link: "Link",
  copy: "Copy", copied: "Copied!", projector: "Projector view", present: "Present",
  addActivity: "Add activity", noActivities: "Add an activity above – your class sees it instantly.",
  settings: "Settings", deleteSession: "Delete session", confirmDelete: "Really delete? All answers will be lost.",
  localhostWarn: "Phones can't open “localhost”. Open ClassPulse via this address so the QR code works:",
  poll: "Poll", questions: "Q&A", ideas: "Ideas", music: "Music wishes", quiz: "Quiz",
  single: "Single choice", multi: "Multiple choice", yesno: "Yes / No", scale: "Scale 1–10", text: "Free text", ranking: "Ranking",
  yes: "Yes", no: "No",
  question: "Question", yourQuestion: "Your question for the class", options: "Answers", addOption: "Add answer",
  option: "Answer", randomQuestion: "Random question", showResults: "Results for the class",
  resultsLive: "Show live", resultsAfter: "Only when closed",
  start: "Start", approvalOn: "With approval", approvalOff: "No approval", topic: "Topic (optional)", moderation: "Only visible after my approval",
  explicit: "Allow songs marked “explicit”", syncSpotify: "Sync with a Spotify playlist",
  closeActivity: "Close", openActivity: "Open", reset: "Reset", confirmReset: "Delete all answers of this activity?",
  votes: "votes", vote: "vote", average: "Average", points: "points", noVotesYet: "No answers yet",
  pending: "Waiting", approved: "Visible", rejected: "Rejected", done: "Done",
  approve: "Approve", reject: "Reject", markDone: "Done", answer: "Answer", answerPlaceholder: "Answer for the class…",
  sortTop: "Top", sortNew: "Newest", waitingApproval: "waiting for approval", nothingYet: "Nothing here yet",
  openPlaylist: "Open playlist in Spotify", inPlaylist: "In playlist", spotifyError: "Spotify error – song was not synced. Is Spotify still connected?",
  quizTitle: "Quiz title", addQuestion: "Add question", seconds: "seconds", correct: "correct",
  markCorrect: "Tap the circle to mark the right answer", quizStart: "Show first question",
  quizNext: "Next question", quizReveal: "Reveal", quizFinish: "End quiz", quizRestart: "Restart",
  quizWaiting: "Starting soon!", quizFinished: "Quiz finished", answers: "answers", players: "players",
  topScores: "Leaderboard (anonymous)", yourScore: "Your points", yourRank: "Your rank", of: "of",
  answered: "Answer sent!", timeLeft: "seconds left", rightAnswer: "Correct!", wrongAnswer: "Not quite",
  questionN: "Question {n} of {m}",
  filter: "Content filter", filterLow: "Relaxed", filterMedium: "Normal", filterHigh: "Strict",
  filterHelpLow: "Blocks only severe content: threats, hate, sexual content, extremism.",
  filterHelpMedium: "Also insults, ads and links. Recommended.",
  filterHelpHigh: "Also swear words and ALL-CAPS shouting.",
  blockedWords: "Additional blocked words", allowedWords: "Allowed words (if something is blocked by mistake)",
  wordsHint: "Separate with commas", language: "Language",
  spotify: "Spotify", spotifyConnect: "Connect Spotify", spotifyConnected: "Connected as", spotifyDisconnect: "Disconnect",
  spotifyNotConfigured: "Spotify is not set up on this server. Music wishes still work – as text.",
  spotifyHelp: "Approved songs are then added to a playlist automatically.",
  account: "Account", deleteAccount: "Delete account and all data", confirmDeleteAccount: "Permanently delete your account and all sessions?",
  privacyNote: "Students stay anonymous: no names, no accounts, no IP addresses in the database.",
  joinTitle: "Join", enterCode: "Enter the code from the board", join: "Let's go",
  anonymous: "You are anonymous. Nobody – not even your teacher – can see what came from you.",
  sessionPaused: "Short break – back in a moment.", sessionEnded: "This session has ended. Thanks for taking part!",
  noActivitiesStudent: "Starting soon – wait for your teacher.",
  send: "Send", sent: "Sent!", sentPending: "Sent! Appears after approval.", merged: "Already there – your vote was counted!",
  thanksVote: "Thanks for voting!", resultsLater: "Results will be shown at the end.", closed: "Closed",
  askPlaceholder: "Your question…", ideaPlaceholder: "Your idea…", songPlaceholder: "Search a song…", songTextPlaceholder: "Title – Artist",
  textAnswerPlaceholder: "Your answer…", search: "Search", suggest: "Suggest", rankHint: "Tap the answers in your order",
  resetRank: "Start over", submitVote: "Vote", reconnecting: "Reconnecting…",
  "err.network": "No connection. Please check your internet.",
  "err.session_not_found": "This code doesn't exist. Please check it again.",
  "err.session_ended": "This session has ended.", "err.session_paused": "The session is paused right now.",
  "err.activity_closed": "This activity is closed.", "err.already_voted": "You already voted.",
  "err.already_answered": "You already answered.", "err.question_closed": "This question is over.", "err.time_up": "Time's up.",
  "err.rate_limited": "A bit slower please – try again in a moment.",
  "err.filter:inappropriate": "We can't send this. Please phrase it kindly and respectfully.",
  "err.filter:link": "Links are not allowed here.", "err.filter:spam": "This looks like spam. Please write a normal sentence.",
  "err.filter:too_long": "That's too long. Please keep it shorter.", "err.filter:empty": "Please write something.",
  "err.filter:invalid": "The text contains invalid characters.", "err.filter:duplicate": "You just sent that.",
  "err.filter:explicit": "This song is marked explicit and isn't allowed here.",
  "err.spotify_not_connected": "Spotify is not connected.", "err.spotify_unavailable": "Spotify isn't responding. Try again in a moment.",
  "err.spotify_not_configured": "Spotify is not set up on this server.",
  "err.wrong_credentials": "Email or password is wrong.", "err.email_taken": "An account with this email already exists.",
  "err.registration_closed": "New accounts are disabled on this server.",
  "err.need_two_options": "Please enter at least two answers.", "err.need_questions": "Please add at least one question.",
  "err.invalid": "Please check your input.", "err.error": "Something went wrong. Please try again.",
  spotifyConnectedMsg: "Spotify is now connected.", spotifyErrorMsg: "Connecting Spotify failed. Please try again.",
  randomQuestions: [
    "How do you feel today (1 = tired, 10 = great)?", "What was the most interesting thing today?", "How well did you understand the topic?",
    "Which superpower would you like to have?", "What should we review next?", "How was the pace today?",
    "Where should our next class trip go?", "What made you happy this week?",
  ],
};

export const languages = { de, en };
export type Lang = keyof typeof languages;
type Key = { [K in keyof Dict]: Dict[K] extends string ? K : never }[keyof Dict];

const initial = (): Lang => {
  const saved = store.get("cp_lang");
  if (saved === "de" || saved === "en") return saved;
  return navigator.language?.toLowerCase().startsWith("de") ? "de" : "en";
};

const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({ lang: "de", setLang: () => {} });

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initial);
  const setLang = (l: Lang) => {
    store.set("cp_lang", l);
    document.documentElement.lang = l;
    setLangState(l);
  };
  return <Ctx.Provider value={{ lang, setLang }}>{children}</Ctx.Provider>;
}

export function useT() {
  const { lang, setLang } = useContext(Ctx);
  const d = languages[lang];
  const t = (key: Key, vars?: Record<string, string | number>) => {
    let s = d[key] as string;
    for (const [k, v] of Object.entries(vars ?? {})) s = s.replace(`{${k}}`, String(v));
    return s;
  };
  const err = (e: unknown) => {
    const code = (e as { code?: string })?.code ?? "error";
    return (d as Record<string, unknown>)[`err.${code}`] as string ?? d["err.error"];
  };
  return { t, err, lang, setLang, dict: d };
}
