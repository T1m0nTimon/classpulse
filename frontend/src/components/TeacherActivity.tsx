import { useEffect, useState } from "react";
import { api, type Activity, type Item } from "../api";
import { useT } from "../i18n";
import { PollResults, QuizBoard, QuizQuestionResults, SongLine } from "./Results";
import { KIND_ICON, Segmented } from "./ui";

export function TeacherActivity({ a, onChange, onError, onPresent }: {
  a: Activity; onChange: (a?: Activity) => void; onError: (e: unknown) => void; onPresent: () => void;
}) {
  const { t } = useT();
  const act = async (fn: () => Promise<Activity | unknown>) => {
    try {
      const r = await fn();
      onChange(r && typeof r === "object" && "id" in r ? (r as Activity) : undefined);
    } catch (e) {
      onError(e);
    }
  };
  const patch = (body: object) => act(() => api(`/api/activities/${a.id}`, { method: "PATCH", body }));

  return (
    <section className="card p-5 fade-in" aria-label={a.title}>
      <header className="flex items-start gap-3 mb-4">
        <span className="text-2xl" aria-hidden>{KIND_ICON[a.kind]}</span>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold uppercase tracking-wide muted">{t(a.kind)}{a.poll_type ? ` · ${t(a.poll_type)}` : ""}</div>
          <h3 className="text-lg font-bold break-words">{a.title}</h3>
        </div>
        <span className={`pill ${a.is_open ? "bg-[color-mix(in_srgb,var(--color-ok)_15%,transparent)] text-[var(--color-ok)]" : "bg-[var(--soft)] muted"}`}>
          {a.is_open ? "●" : t("closed")}
        </span>
      </header>

      {a.kind === "poll" && <PollResults a={a} />}
      {a.kind === "quiz" && <QuizControls a={a} act={act} />}
      {(a.kind === "questions" || a.kind === "ideas" || a.kind === "music") && <Moderation a={a} act={act} />}

      <footer className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-[var(--line)]">
        <button className="btn btn-soft btn-sm" onClick={onPresent}>🖥 {t("present")}</button>
        <button className="btn btn-soft btn-sm" onClick={() => patch({ is_open: !a.is_open })}>{a.is_open ? `⏹ ${t("closeActivity")}` : `▶ ${t("openActivity")}`}</button>
        {a.kind === "poll" && (
          <button className="btn btn-soft btn-sm" onClick={() => patch({ results: a.results_mode === "live" ? "after" : "live" })}>
            👁 {a.results_mode === "live" ? t("resultsLive") : t("resultsAfter")}
          </button>
        )}
        {a.kind !== "poll" && a.kind !== "quiz" && (
          <button className="btn btn-soft btn-sm" onClick={() => patch({ moderation: !a.moderation })}>🛡 {a.moderation ? t("approvalOn") : t("approvalOff")}</button>
        )}
        <button className="btn btn-soft btn-sm" onClick={() => confirm(t("confirmReset")) && act(() => api(`/api/activities/${a.id}/reset`, { method: "POST" }))}>↺ {t("reset")}</button>
        <button className="btn btn-danger btn-sm ml-auto" onClick={() => confirm(t("confirmDelete")) && act(() => api(`/api/activities/${a.id}`, { method: "DELETE" }))}>{t("delete")}</button>
      </footer>
    </section>
  );
}

function QuizControls({ a, act }: { a: Activity; act: (fn: () => Promise<unknown>) => void }) {
  const { t } = useT();
  const phase = a.quiz?.phase;
  const ctl = (action: string) => act(() => api(`/api/activities/${a.id}/quiz`, { body: { action } }));
  const remaining = useCountdown(a.question?.remaining, phase === "question");
  return (
    <div className="space-y-4">
      {phase === "waiting" && <p className="muted">{a.questions?.length} {t("question")} · {t("quizWaiting")}</p>}
      {(phase === "question" || phase === "reveal") && (
        <>
          {phase === "question" && <div className="text-3xl font-bold tabular-nums">{Math.ceil(remaining)} <span className="text-base muted font-normal">{t("timeLeft")}</span></div>}
          <QuizQuestionResults a={a} />
        </>
      )}
      {phase === "finished" && <div className="font-bold">{t("quizFinished")} 🎉</div>}
      {(phase === "reveal" || phase === "finished") && <QuizBoard a={a} />}
      <div className="flex flex-wrap gap-2">
        {phase === "waiting" && <button className="btn btn-primary" onClick={() => ctl("next")}>▶ {t("quizStart")}</button>}
        {phase === "question" && <button className="btn btn-primary" onClick={() => ctl("reveal")}>✓ {t("quizReveal")}</button>}
        {phase === "reveal" && <button className="btn btn-primary" onClick={() => ctl("next")}>→ {(a.quiz?.current ?? 0) + 1 < (a.questions?.length ?? 0) ? t("quizNext") : t("quizFinish")}</button>}
        {phase !== "waiting" && <button className="btn btn-soft" onClick={() => confirm(t("confirmReset")) && ctl("restart")}>↺ {t("quizRestart")}</button>}
      </div>
    </div>
  );
}

export function useCountdown(remaining: number | undefined, running: boolean) {
  const [left, setLeft] = useState(remaining ?? 0);
  useEffect(() => {
    if (!running || remaining === undefined) return setLeft(remaining ?? 0);
    const end = Date.now() + remaining * 1000;
    setLeft(remaining);
    const id = window.setInterval(() => setLeft(Math.max(0, (end - Date.now()) / 1000)), 250);
    return () => window.clearInterval(id);
  }, [remaining, running]);
  return left;
}

function Moderation({ a, act }: { a: Activity; act: (fn: () => Promise<unknown>) => void }) {
  const { t } = useT();
  const [sort, setSort] = useState<"top" | "new">("top");
  const [filter, setFilter] = useState<"open" | "done">("open");
  const items = [...(a.items ?? [])]
    .filter((i) => (filter === "open" ? i.status !== "rejected" && i.status !== "done" : i.status === "done" || i.status === "rejected"))
    .sort((x, y) => (sort === "top" ? y.votes - x.votes : 0) || y.created_at.localeCompare(x.created_at));
  const pendingCount = (a.items ?? []).filter((i) => i.status === "pending").length;
  return (
    <div className="space-y-3">
      {a.kind === "music" && a.playlist_url && (
        <a className="btn btn-soft btn-sm" href={a.playlist_url} target="_blank" rel="noopener noreferrer">🎧 {t("openPlaylist")}</a>
      )}
      {a.spotify_error && <p className="text-sm text-[var(--color-bad)]">{t("spotifyError")}</p>}
      <div className="flex gap-2 flex-wrap">
        <div className="flex-1 min-w-[180px]"><Segmented value={filter} onChange={setFilter} options={[{ value: "open", label: `${t("open")}${pendingCount ? ` (${pendingCount} ${t("pending")})` : ""}` }, { value: "done", label: `${t("done")} / ${t("rejected")}` }]} /></div>
        <div className="flex-1 min-w-[180px]"><Segmented value={sort} onChange={setSort} options={[{ value: "top", label: t("sortTop") }, { value: "new", label: t("sortNew") }]} /></div>
      </div>
      {!items.length && <p className="muted py-2">{t("nothingYet")}</p>}
      <ul className="space-y-2">
        {items.map((i) => <ModItem key={i.id} item={i} kind={a.kind} act={act} />)}
      </ul>
    </div>
  );
}

function ModItem({ item, kind, act }: { item: Item; kind: string; act: (fn: () => Promise<unknown>) => void }) {
  const { t } = useT();
  const [answering, setAnswering] = useState(false);
  const [answer, setAnswer] = useState(item.answer);
  const set = (body: object) => act(() => api(`/api/submissions/${item.id}`, { method: "PATCH", body }));
  return (
    <li className={`rounded-2xl p-3 ${item.status === "pending" ? "border-2 border-dashed border-[var(--color-warn)]" : "bg-[var(--soft)]"}`}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <SongLine item={item} />
          {item.answer && !answering && <p className="mt-1.5 text-sm"><span className="muted">↳</span> {item.answer}</p>}
        </div>
        <div className="text-right shrink-0">
          <div className="font-bold tabular-nums">▲ {item.votes}</div>
          {item.in_playlist && <div className="text-xs text-[var(--color-ok)]">{t("inPlaylist")}</div>}
        </div>
      </div>
      {answering && (
        <div className="mt-2 flex gap-2">
          <input className="field" autoFocus value={answer} maxLength={2000} placeholder={t("answerPlaceholder")} onChange={(e) => setAnswer(e.target.value)} />
          <button className="btn btn-primary" onClick={() => { set({ answer, status: item.status === "pending" ? "approved" : item.status }); setAnswering(false); }}>{t("save")}</button>
        </div>
      )}
      <div className="flex flex-wrap gap-2 mt-2">
        {item.status === "pending" && <button className="btn btn-primary btn-sm" onClick={() => set({ status: "approved" })}>✓ {t("approve")}</button>}
        {item.status !== "rejected" && item.status !== "done" && kind === "questions" && <button className="btn btn-soft btn-sm" onClick={() => setAnswering(!answering)}>💬 {t("answer")}</button>}
        {item.status === "approved" && <button className="btn btn-soft btn-sm" onClick={() => set({ status: "done" })}>✔ {t("markDone")}</button>}
        {(item.status === "done" || item.status === "rejected") && <button className="btn btn-soft btn-sm" onClick={() => set({ status: "approved" })}>↺ {t("approved")}</button>}
        {item.status !== "rejected" && <button className="btn btn-soft btn-sm" onClick={() => set({ status: "rejected" })}>✕ {t("reject")}</button>}
        <button className="btn btn-danger btn-sm ml-auto" aria-label={t("delete")} onClick={() => act(() => api(`/api/submissions/${item.id}`, { method: "DELETE" }))}>🗑</button>
      </div>
    </li>
  );
}
