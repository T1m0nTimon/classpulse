import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, type Activity, type ClassSession, type Kind } from "../api";
import { useApp } from "../App";
import { Creator, type ActivityBody } from "../components/Creator";
import { PollResults, QuizBoard, QuizQuestionResults, SongLine } from "../components/Results";
import { TeacherActivity, useCountdown } from "../components/TeacherActivity";
import { KIND_ICON, Segmented, Sheet, useToast } from "../components/ui";
import { useT } from "../i18n";
import { useLive, useThrottled } from "../live";
import { StatusPill } from "./Home";

export default function SessionPage() {
  const { id } = useParams();
  const { teacher, config } = useApp();
  const { t, err } = useT();
  const nav = useNavigate();
  const toast = useToast();
  const [s, setS] = useState<ClassSession | null>(null);
  const [participants, setParticipants] = useState(0);
  const [creating, setCreating] = useState<Kind | null>(null);
  const [present, setPresent] = useState<string | "qr" | null>(null);
  const [settings, setSettings] = useState(false);
  const [spotify, setSpotify] = useState(false);

  const load = useCallback(() => {
    api<ClassSession>(`/api/sessions/${id}`).then(setS).catch((e) => (e.status === 404 ? nav("/") : toast.bad(err(e))));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);
  const refresh = useThrottled(load);

  useEffect(() => {
    if (!teacher) {
      nav("/");
      return;
    }
    load();
    api("/api/spotify/status").then((r) => setSpotify(r.connected)).catch(() => {});
  }, [teacher, load, nav]);

  const connected = useLive(teacher ? `/ws/t/${id}` : null, (e) => {
    if (e.type === "participants") setParticipants(e.count);
    else if (e.type === "deleted") nav("/");
    else refresh();
  }, load);

  if (!s) return <div className="min-h-dvh" />;
  const base = config?.public_url ?? location.origin;
  const joinUrl = `${base}/j/${s.code}`;
  const isLocalhost = !config?.public_url && ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);

  const setStatus = (status: string) => api<ClassSession>(`/api/sessions/${s.id}`, { method: "PATCH", body: { status } }).then(setS).catch((e) => toast.bad(err(e)));
  const create = async (body: ActivityBody) => {
    try {
      await api(`/api/sessions/${s.id}/activities`, { body });
      setCreating(null);
      load();
    } catch (e) {
      toast.bad(err(e));
    }
  };
  const replaceActivity = (a?: Activity) => (a ? setS({ ...s, activities: s.activities?.map((x) => (x.id === a.id ? a : x)) }) : load());

  return (
    <main className="max-w-6xl mx-auto p-4 sm:p-6 pb-16">
      <header className="flex items-center gap-3 mb-5 flex-wrap">
        <Link to="/" className="btn btn-soft btn-sm" aria-label={t("back")}>‹ {t("back")}</Link>
        <h1 className="text-2xl font-bold flex-1 min-w-[160px] truncate">{s.title}</h1>
        <StatusPill status={s.status} />
        {s.status === "live" && <button className="btn btn-soft" onClick={() => setStatus("paused")}>⏸ {t("pause")}</button>}
        {s.status === "paused" && <button className="btn btn-primary" onClick={() => setStatus("live")}>▶ {t("resume")}</button>}
        {s.status !== "ended" ? (
          <button className="btn btn-danger" onClick={() => setStatus("ended")}>⏹ {t("end")}</button>
        ) : (
          <button className="btn btn-primary" onClick={() => setStatus("live")}>↺ {t("reopen")}</button>
        )}
        <button className="btn btn-soft" aria-label={t("settings")} onClick={() => setSettings(true)}>⚙︎</button>
      </header>
      {!connected && <p className="mb-3 text-sm text-[var(--color-warn)]">{t("reconnecting")}</p>}

      <div className="grid lg:grid-cols-[340px_1fr] gap-5 items-start">
        <aside className="card p-5 lg:sticky lg:top-5 text-center">
          <p className="muted text-sm mb-3">{t("joinHow")}</p>
          <button onClick={() => setPresent("qr")} className="block w-full" aria-label={t("projector")}>
            <img src={`/api/sessions/${s.id}/qr.svg?base=${encodeURIComponent(base)}`} alt={joinUrl} className="w-full max-w-[260px] mx-auto rounded-xl bg-white p-1" />
          </button>
          <div className="text-4xl font-mono font-bold tracking-[.15em] mt-3 select-all">{s.code}</div>
          <CopyLink url={joinUrl} />
          <div className="mt-4 text-3xl font-bold tabular-nums">👥 {participants}</div>
          <div className="muted text-sm">{t("participants")}</div>
          <button className="btn btn-primary w-full mt-4" onClick={() => setPresent("qr")}>🖥 {t("projector")}</button>
          {isLocalhost && config?.lan_url && (
            <p className="text-sm mt-4 p-3 rounded-xl bg-[color-mix(in_srgb,var(--color-warn)_15%,transparent)] text-left">
              ⚠️ {t("localhostWarn")} <a className="font-semibold underline break-all" href={`${config.lan_url}/s/${s.id}`}>{config.lan_url}</a>
            </p>
          )}
        </aside>

        <section className="space-y-4 min-w-0">
          <div className="card p-4">
            <div className="text-sm font-semibold muted mb-2">{t("addActivity")}</div>
            <div className="grid grid-cols-5 gap-2">
              {(["poll", "questions", "ideas", "music", "quiz"] as Kind[]).map((k) => (
                <button key={k} className="rounded-2xl bg-[var(--soft)] min-h-[76px] p-2 flex flex-col items-center justify-center gap-1 hover:ring-2 hover:ring-[var(--color-accent)] active:scale-95 transition" onClick={() => setCreating(k)}>
                  <span className="text-2xl" aria-hidden>{KIND_ICON[k]}</span>
                  <span className="text-xs sm:text-sm font-semibold text-center leading-tight">{t(k)}</span>
                </button>
              ))}
            </div>
          </div>
          {!s.activities?.length && <p className="muted text-center py-8">{t("noActivities")}</p>}
          {[...(s.activities ?? [])].reverse().map((a) => (
            <TeacherActivity key={a.id} a={a} onChange={replaceActivity} onError={(e) => toast.bad(err(e))} onPresent={() => setPresent(a.id)} />
          ))}
        </section>
      </div>

      {creating && <Creator kind={creating} spotify={spotify} onCancel={() => setCreating(null)} onCreate={create} />}
      {settings && <SessionSettings s={s} onSaved={setS} onClose={() => setSettings(false)} onDeleted={() => nav("/")} />}
      {present && <Presenter s={s} joinUrl={joinUrl} base={base} which={present} participants={participants} onClose={() => setPresent(null)} />}
      {toast.node}
    </main>
  );
}

function CopyLink({ url }: { url: string }) {
  const { t } = useT();
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setDone(true);
      window.setTimeout(() => setDone(false), 2000);
    } catch {
      prompt(t("link"), url); // older iPads without clipboard permission
    }
  };
  return (
    <button onClick={copy} className="mt-2 text-sm text-[var(--color-accent)] break-all hover:underline">
      {done ? `✓ ${t("copied")}` : url.replace(/^https?:\/\//, "")}
    </button>
  );
}

/** Fullscreen projector view: large QR + code, or one activity's live results with a small QR. */
function Presenter({ s, joinUrl, base, which, participants, onClose }: {
  s: ClassSession; joinUrl: string; base: string; which: string; participants: number; onClose: () => void;
}) {
  const { t } = useT();
  const a = s.activities?.find((x) => x.id === which);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.documentElement.requestFullscreen?.().catch(() => {}); // not available on iPhone; fine
    return () => {
      window.removeEventListener("keydown", onKey);
      if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    };
  }, [onClose]);
  const qr = `/api/sessions/${s.id}/qr.svg?base=${encodeURIComponent(base)}`;
  return (
    <div className="fixed inset-0 z-50 bg-[var(--bg)] overflow-y-auto fade-in" style={{ padding: "max(1.5rem, env(safe-area-inset-top)) max(1.5rem, env(safe-area-inset-right)) max(1.5rem, env(safe-area-inset-bottom)) max(1.5rem, env(safe-area-inset-left))" }}>
      <button className="btn btn-soft fixed top-4 right-4 z-10" onClick={onClose}>✕ {t("close")}</button>
      {!a ? (
        <div className="min-h-full flex flex-col items-center justify-center text-center gap-6">
          <h2 className="text-4xl sm:text-5xl font-bold">{s.title}</h2>
          <img src={qr} alt={joinUrl} className="w-[min(70vh,80vw)] rounded-3xl bg-white p-3" />
          <div className="text-6xl sm:text-8xl font-mono font-bold tracking-[.15em]">{s.code}</div>
          <div className="text-2xl muted break-all">{joinUrl.replace(/^https?:\/\//, "")}</div>
          <div className="text-3xl font-bold">👥 {participants}</div>
        </div>
      ) : (
        <div className="max-w-5xl mx-auto grid md:grid-cols-[1fr_220px] gap-8 items-start pt-12">
          <div>
            <div className="text-xl muted">{KIND_ICON[a.kind]} {t(a.kind)}</div>
            <h2 className="text-4xl sm:text-5xl font-bold mb-8 break-words">{a.title}</h2>
            <PresentBody a={a} />
          </div>
          <div className="text-center">
            <img src={qr} alt={joinUrl} className="w-full rounded-2xl bg-white p-2" />
            <div className="text-4xl font-mono font-bold tracking-[.12em] mt-2">{s.code}</div>
            <div className="text-xl mt-2">👥 {participants}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function PresentBody({ a }: { a: Activity }) {
  const { t } = useT();
  const remaining = useCountdown(a.question?.remaining, a.quiz?.phase === "question");
  if (a.kind === "poll") return <PollResults a={a} big />;
  if (a.kind === "quiz") {
    const phase = a.quiz?.phase;
    if (phase === "question" && a.question) {
      return (
        <div className="text-2xl">
          <div className="muted">{t("questionN", { n: a.question.index + 1, m: a.question.count })} · ⏱ {Math.ceil(remaining)}</div>
          <div className="text-4xl font-bold my-6">{a.question.text}</div>
          <div className="grid sm:grid-cols-2 gap-3">
            {a.question.options.map((o, i) => <div key={i} className="card p-5 text-2xl font-semibold">{["🔴", "🔵", "🟡", "🟢", "🟣", "🟠"][i]} {o}</div>)}
          </div>
          <div className="mt-4 muted">{a.quiz?.per_question?.[a.question.index]?.answers ?? 0} {t("answers")}</div>
        </div>
      );
    }
    if (phase === "reveal") return <div className="space-y-8"><QuizQuestionResults a={a} big /><QuizBoard a={a} big /></div>;
    if (phase === "finished") return <QuizBoard a={a} big />;
    return <p className="text-3xl muted">{t("quizWaiting")}</p>;
  }
  const items = (a.items ?? []).filter((i) => i.status === "approved" || i.status === "done").sort((x, y) => y.votes - x.votes);
  if (!items.length) return <p className="text-2xl muted">{t("nothingYet")}</p>;
  return (
    <ul className="space-y-3 text-2xl">
      {items.slice(0, 12).map((i) => (
        <li key={i.id} className={`card p-5 flex items-center gap-4 ${i.status === "done" ? "opacity-50" : ""}`}>
          <div className="flex-1 min-w-0"><SongLine item={i} />{i.answer && <p className="text-xl muted mt-1">↳ {i.answer}</p>}</div>
          <span className="font-bold tabular-nums">▲ {i.votes}</span>
        </li>
      ))}
    </ul>
  );
}

function SessionSettings({ s, onSaved, onClose, onDeleted }: { s: ClassSession; onSaved: (s: ClassSession) => void; onClose: () => void; onDeleted: () => void }) {
  const { t, err } = useT();
  const [title, setTitle] = useState(s.title);
  const [level, setLevel] = useState(s.filter_level ?? "medium");
  const [blocked, setBlocked] = useState((s.blocked_words ?? []).join(", "));
  const [allowed, setAllowed] = useState((s.allowed_words ?? []).join(", "));
  const [error, setError] = useState("");
  const split = (x: string) => x.split(",").map((w) => w.trim()).filter(Boolean);
  const save = async () => {
    try {
      onSaved(await api<ClassSession>(`/api/sessions/${s.id}`, { method: "PATCH", body: { title, filter_level: level, blocked_words: split(blocked), allowed_words: split(allowed) } }));
      onClose();
    } catch (e) {
      setError(err(e));
    }
  };
  const del = async () => {
    if (!confirm(t("confirmDelete"))) return;
    await api(`/api/sessions/${s.id}`, { method: "DELETE" }).catch(() => {});
    onDeleted();
  };
  const help = { low: t("filterHelpLow"), medium: t("filterHelpMedium"), high: t("filterHelpHigh") }[level];
  return (
    <Sheet title={t("settings")} onClose={onClose}>
      <div className="space-y-5">
        <input className="field" value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} aria-label={t("topic")} />
        <div>
          <h3 className="font-semibold mb-2">🛡 {t("filter")}</h3>
          <Segmented value={level} onChange={setLevel} options={[{ value: "low", label: t("filterLow") }, { value: "medium", label: t("filterMedium") }, { value: "high", label: t("filterHigh") }]} />
          <p className="text-sm muted mt-2">{help}</p>
        </div>
        <label className="block"><span className="text-sm font-semibold">{t("blockedWords")}</span>
          <textarea className="field mt-1" rows={2} value={blocked} onChange={(e) => setBlocked(e.target.value)} placeholder={t("wordsHint")} /></label>
        <label className="block"><span className="text-sm font-semibold">{t("allowedWords")}</span>
          <textarea className="field mt-1" rows={2} value={allowed} onChange={(e) => setAllowed(e.target.value)} placeholder={t("wordsHint")} /></label>
        {error && <p className="text-[var(--color-bad)] text-sm">{error}</p>}
        <button className="btn btn-primary w-full" onClick={save}>{t("save")}</button>
        <button className="btn btn-danger w-full" onClick={del}>{t("deleteSession")}</button>
      </div>
    </Sheet>
  );
}
