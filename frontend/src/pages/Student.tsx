import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import { api, store, type Activity, type Item, type Song } from "../api";
import { PollResults, QuizBoard, SongLine } from "../components/Results";
import { useCountdown } from "../components/TeacherActivity";
import { KIND_ICON, Logo, useToast } from "../components/ui";
import { useT } from "../i18n";
import { useLive, useThrottled } from "../live";

interface View { title: string; code: string; status: string; language: "de" | "en"; spotify: boolean; activities: Activity[] }

/** The device token is random and stays on this device only; it is what prevents double voting. */
async function getToken(code: string): Promise<string> {
  const key = `cp_p_${code}`;
  const existing = store.get(key);
  if (existing) return existing;
  const { token } = await api<{ token: string }>(`/api/p/${code}/join`, { method: "POST" });
  store.set(key, token);
  return token;
}

export default function Student() {
  const { code = "" } = useParams();
  const { t, err } = useT();
  const toast = useToast();
  const [token, setToken] = useState<string | null>(null);
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState("");
  const C = code.toUpperCase();

  useEffect(() => {
    getToken(C).then(setToken).catch((e) => setError(err(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [C]);

  const load = useCallback(() => {
    if (!token) return;
    api<View>(`/api/p/${C}`, { participant: token }).then(setView).catch((e) => setError(err(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, C]);
  const refresh = useThrottled(load, 300);
  useEffect(load, [load]);
  const connected = useLive(token ? `/ws/p/${C}` : null, refresh, load);

  if (error && !view) {
    return (
      <main className="min-h-dvh flex items-center justify-center p-6 text-center">
        <div><div className="text-5xl mb-4">🤔</div><p className="text-xl font-semibold">{error}</p><Link to="/j" className="btn btn-primary mt-6">← {t("enterCode")}</Link></div>
      </main>
    );
  }
  if (!view || !token) return <div className="min-h-dvh" />;
  const ctx = { code: C, token, reload: load, ok: toast.ok, bad: (e: unknown) => toast.bad(err(e)) };

  return (
    <main className="max-w-xl mx-auto p-4 pb-16">
      <header className="flex items-center gap-2.5 py-2 mb-4">
        <Logo size={28} />
        <h1 className="font-bold text-lg flex-1 truncate">{view.title}</h1>
        <span className="font-mono text-sm muted">{view.code}</span>
      </header>
      {!connected && <p className="mb-3 text-sm text-[var(--color-warn)]">{t("reconnecting")}</p>}
      {view.status === "paused" && <Notice icon="☕️" text={t("sessionPaused")} />}
      {view.status === "ended" && <Notice icon="👋" text={t("sessionEnded")} />}
      {view.status === "live" && !view.activities.length && <Notice icon="⏳" text={t("noActivitiesStudent")} />}
      <div className="space-y-4">
        {view.status === "live" && [...view.activities].reverse().map((a) => (
          <section key={a.id} className={`card p-5 fade-in ${a.is_open ? "" : "opacity-70"}`} aria-label={a.title}>
            <div className="text-xs font-semibold uppercase tracking-wide muted">{KIND_ICON[a.kind]} {t(a.kind)}{!a.is_open && ` · ${t("closed")}`}</div>
            <h2 className="text-xl font-bold mt-1 mb-4 break-words">{a.title}</h2>
            {a.kind === "poll" && <PollCard a={a} {...ctx} />}
            {a.kind === "quiz" && <QuizCard a={a} {...ctx} />}
            {(a.kind === "questions" || a.kind === "ideas" || a.kind === "music") && <SubmitCard a={a} spotify={view.spotify} {...ctx} />}
          </section>
        ))}
      </div>
      <p className="text-xs muted text-center mt-8 px-4">🔒 {t("anonymous")}</p>
      {toast.node}
    </main>
  );
}

function Notice({ icon, text }: { icon: string; text: string }) {
  return <div className="card p-8 text-center fade-in"><div className="text-5xl mb-3">{icon}</div><p className="text-lg font-semibold">{text}</p></div>;
}

interface Ctx { code: string; token: string; reload: () => void; ok: (m: string) => void; bad: (e: unknown) => void }

function PollCard({ a, code, token, reload, ok, bad }: { a: Activity } & Ctx) {
  const { t } = useT();
  const [choice, setChoice] = useState<number[]>([]);
  const [value, setValue] = useState(5);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const opts = a.options ?? [];

  if (a.voted || !a.is_open) {
    return (
      <div>
        {a.voted && <p className="font-semibold text-[var(--color-ok)] mb-3">✓ {t("thanksVote")}</p>}
        {a.results ? <PollResults a={a} /> : <p className="muted">{t("resultsLater")}</p>}
      </div>
    );
  }
  const send = async (payload: object) => {
    setBusy(true);
    try {
      await api(`/api/p/${code}/a/${a.id}/vote`, { body: { payload }, participant: token });
      ok(t("thanksVote"));
      reload();
    } catch (e) {
      bad(e);
    } finally {
      setBusy(false);
    }
  };
  const big = "w-full min-h-[60px] rounded-2xl px-4 text-left text-lg font-semibold border-2 transition active:scale-[.98]";

  switch (a.poll_type) {
    case "single":
    case "yesno":
      return (
        <div className="space-y-2.5">
          {opts.map((o, i) => (
            <button key={i} disabled={busy} className={`${big} border-[var(--line)] hover:border-[var(--color-accent)]`} onClick={() => send({ choice: i })}>{o}</button>
          ))}
        </div>
      );
    case "multi":
      return (
        <div className="space-y-2.5">
          {opts.map((o, i) => {
            const on = choice.includes(i);
            return (
              <button key={i} aria-pressed={on} className={`${big} ${on ? "border-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent)_10%,transparent)]" : "border-[var(--line)]"}`}
                onClick={() => setChoice(on ? choice.filter((c) => c !== i) : [...choice, i])}>{on ? "☑︎" : "☐"} {o}</button>
            );
          })}
          <button className="btn btn-primary w-full" disabled={busy || !choice.length} onClick={() => send({ choices: choice })}>{t("submitVote")}</button>
        </div>
      );
    case "scale":
      return (
        <div>
          <div className="text-6xl font-bold text-center tabular-nums mb-2">{value}</div>
          <input type="range" min={1} max={10} value={value} onChange={(e) => setValue(Number(e.target.value))} className="w-full h-10 accent-[var(--color-accent)]" aria-label={t("scale")} />
          <div className="flex justify-between muted text-sm mb-4"><span>1</span><span>10</span></div>
          <button className="btn btn-primary w-full" disabled={busy} onClick={() => send({ value })}>{t("submitVote")}</button>
        </div>
      );
    case "ranking":
      return (
        <div className="space-y-2.5">
          <p className="muted text-sm">{t("rankHint")}</p>
          {opts.map((o, i) => {
            const pos = choice.indexOf(i);
            return (
              <button key={i} disabled={pos >= 0} className={`${big} flex items-center gap-3 ${pos >= 0 ? "border-[var(--color-accent)]" : "border-[var(--line)]"}`}
                onClick={() => setChoice([...choice, i])}>
                <span className="w-8 h-8 rounded-full grid place-items-center bg-[var(--soft)] font-bold shrink-0">{pos >= 0 ? pos + 1 : ""}</span>{o}
              </button>
            );
          })}
          <div className="flex gap-2">
            <button className="btn btn-soft" onClick={() => setChoice([])}>{t("resetRank")}</button>
            <button className="btn btn-primary flex-1" disabled={busy || choice.length !== opts.length} onClick={() => send({ order: choice })}>{t("submitVote")}</button>
          </div>
        </div>
      );
    default:
      return (
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (text.trim()) send({ text }); }}>
          <input className="field" value={text} maxLength={300} placeholder={t("textAnswerPlaceholder")} onChange={(e) => setText(e.target.value)} enterKeyHint="send" />
          <button className="btn btn-primary" disabled={busy || !text.trim()}>{t("send")}</button>
        </form>
      );
  }
}

function QuizCard({ a, code, token, reload, bad }: { a: Activity } & Ctx) {
  const { t } = useT();
  const phase = a.quiz?.phase;
  const q = a.question;
  const remaining = useCountdown(q?.remaining, phase === "question");
  const mine = q ? a.quiz?.my_answers?.[String(q.index)] : undefined;
  const [sending, setSending] = useState(false);

  const answer = async (choice: number) => {
    setSending(true);
    try {
      await api(`/api/p/${code}/a/${a.id}/answer`, { body: { index: q!.index, choice }, participant: token });
      reload();
    } catch (e) {
      bad(e);
    } finally {
      setSending(false);
    }
  };
  const colors = ["#ff453a", "#0a84ff", "#ffd60a", "#30d158", "#bf5af2", "#ff9f0a"];

  if (phase === "waiting") return <p className="text-lg muted">⏳ {t("quizWaiting")}</p>;
  if (phase === "finished") {
    return (
      <div className="text-center">
        <div className="text-5xl mb-2">🏁</div>
        <div className="text-lg">{t("yourScore")}: <b className="tabular-nums">{a.quiz?.my_score ?? 0}</b></div>
        {a.quiz?.my_rank && <div className="text-lg">{t("yourRank")}: <b>{a.quiz.my_rank}</b> {t("of")} {a.quiz.players}</div>}
        <div className="mt-4 text-left"><QuizBoard a={a} /></div>
      </div>
    );
  }
  if (!q) return null;
  const answered = mine !== undefined;
  const timeUp = phase === "question" && remaining <= 0;
  return (
    <div>
      <div className="flex justify-between muted text-sm mb-1">
        <span>{t("questionN", { n: q.index + 1, m: q.count })}</span>
        {phase === "question" && <span className="tabular-nums font-bold">⏱ {Math.ceil(remaining)}</span>}
      </div>
      {phase === "question" && <div className="h-1.5 rounded-full bg-[var(--soft)] mb-3 overflow-hidden"><div className="h-full bg-[var(--color-accent)] transition-[width] duration-300" style={{ width: `${(remaining / q.seconds) * 100}%` }} /></div>}
      <p className="text-lg font-semibold mb-4">{q.text}</p>
      <div className="grid grid-cols-2 gap-2.5">
        {q.options.map((o, i) => {
          const isCorrect = q.correct?.includes(i);
          const picked = mine === i;
          const dim = (answered && !picked) || (phase === "reveal" && !isCorrect);
          return (
            <button key={i} disabled={answered || phase !== "question" || sending || timeUp}
              className={`min-h-[84px] rounded-2xl p-3 text-white font-bold text-lg break-words transition active:scale-95 ${dim ? "opacity-35" : ""} ${picked ? "ring-4 ring-[var(--text)]" : ""}`}
              style={{ background: colors[i] }} onClick={() => answer(i)}>
              {phase === "reveal" && isCorrect ? "✓ " : ""}{o}
            </button>
          );
        })}
      </div>
      {phase === "question" && answered && <p className="mt-4 text-center font-semibold">✓ {t("answered")}</p>}
      {phase === "reveal" && (
        <div className="mt-4 text-center">
          {answered && <p className="text-2xl font-bold">{q.correct?.includes(mine!) ? `🎉 ${t("rightAnswer")}` : `😕 ${t("wrongAnswer")}`}</p>}
          <p className="mt-1">{t("yourScore")}: <b className="tabular-nums">{a.quiz?.my_score ?? 0}</b>{a.quiz?.my_rank ? ` · ${t("yourRank")} ${a.quiz.my_rank}/${a.quiz.players}` : ""}</p>
        </div>
      )}
    </div>
  );
}

function SubmitCard({ a, spotify, code, token, reload, ok, bad }: { a: Activity; spotify: boolean } & Ctx) {
  const { t } = useT();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const useSpotify = a.kind === "music" && spotify;
  const send = async (body: object) => {
    setBusy(true);
    try {
      const r = await api(`/api/p/${code}/a/${a.id}/submit`, { body, participant: token });
      ok(r.merged ? t("merged") : r.status === "pending" ? t("sentPending") : t("sent"));
      setText("");
      reload();
      return true;
    } catch (e) {
      bad(e);
      return false;
    } finally {
      setBusy(false);
    }
  };
  const upvote = async (item: Item) => {
    try {
      await api(`/api/p/${code}/a/${a.id}/upvote/${item.id}`, { method: "POST", participant: token });
      reload();
    } catch (e) {
      bad(e);
    }
  };
  const placeholder = a.kind === "questions" ? t("askPlaceholder") : a.kind === "ideas" ? t("ideaPlaceholder") : t("songTextPlaceholder");

  return (
    <div className="space-y-4">
      {a.is_open && (useSpotify ? <SongSearch a={a} code={code} token={token} onPick={(s) => send({ track_id: s.id })} bad={bad} busy={busy} /> : (
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (text.trim()) send({ text }); }}>
          {a.kind === "music"
            ? <input className="field" value={text} maxLength={300} placeholder={placeholder} onChange={(e) => setText(e.target.value)} enterKeyHint="send" />
            : <textarea className="field resize-none" rows={2} value={text} maxLength={500} placeholder={placeholder} onChange={(e) => setText(e.target.value)} enterKeyHint="send" />}
          <button className="btn btn-primary self-stretch !rounded-2xl" disabled={busy || !text.trim()}>{t("send")}</button>
        </form>
      ))}
      <ul className="space-y-2">
        {a.items?.map((i) => (
          <li key={i.id} className={`rounded-2xl bg-[var(--soft)] p-3 flex items-center gap-3 ${i.status === "done" ? "opacity-60" : ""}`}>
            <div className="flex-1 min-w-0">
              <SongLine item={i} />
              {i.answer && <p className="text-sm mt-1"><span className="muted">↳</span> {i.answer}</p>}
            </div>
            <button disabled={!a.is_open} aria-pressed={i.voted} aria-label={`▲ ${i.votes}`} onClick={() => upvote(i)}
              className={`min-w-[56px] min-h-[48px] rounded-xl font-bold tabular-nums flex flex-col items-center justify-center transition active:scale-90 ${i.voted ? "bg-[var(--color-accent)] text-white" : "bg-[var(--card)]"}`}>
              <span className="text-xs leading-none">▲</span>{i.votes}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SongSearch({ a, code, token, onPick, bad, busy }: { a: Activity; code: string; token: string; onPick: (s: Song) => Promise<boolean>; bad: (e: unknown) => void; busy: boolean }) {
  const { t } = useT();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Song[]>([]);
  const timer = useRef<number | undefined>(undefined);
  const search = (value: string) => {
    setQ(value);
    window.clearTimeout(timer.current);
    if (value.trim().length < 2) return setResults([]);
    timer.current = window.setTimeout(() => {
      api<Song[]>(`/api/p/${code}/a/${a.id}/search?q=${encodeURIComponent(value.trim())}`, { participant: token }).then(setResults).catch(bad);
    }, 350);
  };
  return (
    <div>
      <input className="field" type="search" value={q} placeholder={`🔎 ${t("songPlaceholder")}`} onChange={(e) => search(e.target.value)} enterKeyHint="search" autoCorrect="off" />
      {results.length > 0 && (
        <ul className="mt-2 space-y-1.5">
          {results.map((s) => (
            <li key={s.id}>
              <button disabled={busy} className="w-full p-2 rounded-xl hover:bg-[var(--soft)] flex items-center gap-2 text-left"
                onClick={async () => { if (await onPick(s)) { setQ(""); setResults([]); } }}>
                <div className="flex-1 min-w-0"><SongLine item={{ id: s.id, text: "", song: s, status: "", answer: "", votes: 0, created_at: "" }} /></div>
                <span className="btn btn-primary btn-sm shrink-0">+ {t("suggest")}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
