import { useState } from "react";
import type { Kind, PollType, QuizQ } from "../api";
import { useT } from "../i18n";
import { Segmented, Sheet, Toggle } from "./ui";

export type ActivityBody = Record<string, unknown> & { kind: Kind; title: string };

/** One sheet for every activity type. Defaults are chosen so "Start" works right away. */
export function Creator({ kind, spotify, onCancel, onCreate }: {
  kind: Kind; spotify: boolean; onCancel: () => void; onCreate: (body: ActivityBody) => Promise<void>;
}) {
  const { t, dict } = useT();
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState("");
  const [pollType, setPollType] = useState<PollType>("single");
  const [options, setOptions] = useState(["", ""]);
  const [results, setResults] = useState<"live" | "after">("live");
  const [moderation, setModeration] = useState(kind !== "ideas");
  const [explicit, setExplicit] = useState(false);
  const [sync, setSync] = useState(true);
  const [questions, setQuestions] = useState<QuizQ[]>([{ text: "", options: ["", ""], correct: [0], seconds: 20 }]);

  const needsOptions = pollType === "single" || pollType === "multi" || pollType === "ranking";
  const defaultTitle = { poll: t("poll"), questions: t("questions"), ideas: t("ideas"), music: t("music"), quiz: t("quiz") }[kind];

  const submit = async () => {
    setBusy(true);
    const body: ActivityBody = { kind, title: title.trim() || defaultTitle };
    if (kind === "poll") {
      Object.assign(body, {
        poll_type: pollType, results,
        options: pollType === "yesno" ? [t("yes"), t("no")] : options.filter((o) => o.trim()),
      });
    } else if (kind === "quiz") {
      body.questions = questions
        .map((q) => ({ ...q, options: q.options.filter((o) => o.trim()) }))
        .filter((q) => q.text.trim() && q.options.length >= 2)
        .map((q) => ({ ...q, correct: q.correct.filter((i) => i < q.options.length).length ? q.correct.filter((i) => i < q.options.length) : [0] }));
    } else {
      body.moderation = moderation;
      if (kind === "music") Object.assign(body, { allow_explicit: explicit, sync_spotify: sync });
    }
    try {
      await onCreate(body);
    } finally {
      setBusy(false);
    }
  };

  const random = () => {
    const list = dict.randomQuestions;
    const q = list[Math.floor(Math.random() * list.length)];
    setTitle(q);
    if (q.includes("1") && q.includes("10")) setPollType("scale");
    else setPollType("text");
  };

  const canStart = kind === "poll" ? title.trim() && (!needsOptions || options.filter((o) => o.trim()).length >= 2)
    : kind === "quiz" ? questions.some((q) => q.text.trim() && q.options.filter((o) => o.trim()).length >= 2) : true;

  return (
    <Sheet title={t(kind === "quiz" ? "startQuiz" : kind)} onClose={onCancel}>
      <div className="space-y-4">
        {kind === "poll" && (
          <>
            <div>
              <div className="flex gap-2">
                <input className="field" autoFocus placeholder={t("yourQuestion")} value={title} maxLength={300} onChange={(e) => setTitle(e.target.value)} />
                <button className="btn btn-soft shrink-0" onClick={random} title={t("randomQuestion")} aria-label={t("randomQuestion")}>🎲</button>
              </div>
            </div>
            <Segmented value={pollType} onChange={setPollType}
              options={(["single", "multi", "yesno", "scale", "text", "ranking"] as PollType[]).map((v) => ({ value: v, label: t(v) }))} />
            {needsOptions && (
              <div className="space-y-2">
                {options.map((o, i) => (
                  <div key={i} className="flex gap-2">
                    <input className="field" placeholder={`${t("option")} ${i + 1}`} value={o} maxLength={120}
                      onChange={(e) => setOptions(options.map((x, j) => (j === i ? e.target.value : x)))}
                      onKeyDown={(e) => e.key === "Enter" && i === options.length - 1 && options.length < 12 && setOptions([...options, ""])} />
                    {options.length > 2 && <button className="btn btn-soft shrink-0" aria-label={t("delete")} onClick={() => setOptions(options.filter((_, j) => j !== i))}>✕</button>}
                  </div>
                ))}
                {options.length < 12 && <button className="btn btn-soft w-full" onClick={() => setOptions([...options, ""])}>+ {t("addOption")}</button>}
              </div>
            )}
            <div>
              <div className="text-sm muted mb-1.5">{t("showResults")}</div>
              <Segmented value={results} onChange={setResults} options={[{ value: "live", label: t("resultsLive") }, { value: "after", label: t("resultsAfter") }]} />
            </div>
          </>
        )}

        {(kind === "questions" || kind === "ideas" || kind === "music") && (
          <>
            <input className="field" placeholder={t("topic")} value={title} maxLength={300} onChange={(e) => setTitle(e.target.value)} />
            <Toggle checked={moderation} onChange={setModeration} label={t("moderation")} />
            {kind === "music" && (
              <>
                <Toggle checked={explicit} onChange={setExplicit} label={t("explicit")} />
                {spotify ? <Toggle checked={sync} onChange={setSync} label={t("syncSpotify")} /> : <p className="text-sm muted">{t("spotifyNotConfigured")}</p>}
              </>
            )}
          </>
        )}

        {kind === "quiz" && <QuizEditor title={title} setTitle={setTitle} questions={questions} setQuestions={setQuestions} />}

        <button className="btn btn-primary w-full text-lg" disabled={busy || !canStart} onClick={submit}>▶ {t("start")}</button>
      </div>
    </Sheet>
  );
}

function QuizEditor({ title, setTitle, questions, setQuestions }: {
  title: string; setTitle: (s: string) => void; questions: QuizQ[]; setQuestions: (q: QuizQ[]) => void;
}) {
  const { t } = useT();
  const upd = (i: number, q: Partial<QuizQ>) => setQuestions(questions.map((x, j) => (j === i ? { ...x, ...q } : x)));
  return (
    <div className="space-y-4">
      <input className="field" placeholder={t("quizTitle")} value={title} maxLength={300} onChange={(e) => setTitle(e.target.value)} />
      <p className="text-sm muted">{t("markCorrect")}</p>
      {questions.map((q, i) => (
        <div key={i} className="rounded-2xl border border-[var(--line)] p-3 space-y-2">
          <div className="flex gap-2 items-center">
            <span className="font-bold muted w-6 text-center">{i + 1}</span>
            <input className="field" placeholder={t("question")} value={q.text} maxLength={300} onChange={(e) => upd(i, { text: e.target.value })} />
            {questions.length > 1 && <button className="btn btn-soft shrink-0" aria-label={t("delete")} onClick={() => setQuestions(questions.filter((_, j) => j !== i))}>✕</button>}
          </div>
          {q.options.map((o, k) => {
            const isCorrect = q.correct.includes(k);
            return (
              <div key={k} className="flex gap-2 items-center pl-8">
                <button aria-label={t("correct")} aria-pressed={isCorrect}
                  onClick={() => upd(i, { correct: isCorrect ? q.correct.filter((c) => c !== k) : [...q.correct, k] })}
                  className={`w-9 h-9 shrink-0 rounded-full border-2 grid place-items-center font-bold ${isCorrect ? "bg-[var(--color-ok)] border-[var(--color-ok)] text-white" : "border-[var(--line)]"}`}>
                  {isCorrect ? "✓" : ""}
                </button>
                <input className="field" placeholder={`${t("option")} ${k + 1}`} value={o} maxLength={120}
                  onChange={(e) => upd(i, { options: q.options.map((x, j) => (j === k ? e.target.value : x)) })} />
              </div>
            );
          })}
          <div className="flex gap-2 pl-8 flex-wrap">
            {q.options.length < 6 && <button className="btn btn-soft btn-sm" onClick={() => upd(i, { options: [...q.options, ""] })}>+ {t("addOption")}</button>}
            <label className="flex items-center gap-2 text-sm muted ml-auto">
              <select className="field !min-h-[40px] !py-1 !w-auto" value={q.seconds} onChange={(e) => upd(i, { seconds: Number(e.target.value) })}>
                {[10, 20, 30, 45, 60, 90, 120].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              {t("seconds")}
            </label>
          </div>
        </div>
      ))}
      {questions.length < 50 && (
        <button className="btn btn-soft w-full" onClick={() => setQuestions([...questions, { text: "", options: ["", ""], correct: [0], seconds: 20 }])}>+ {t("addQuestion")}</button>
      )}
    </div>
  );
}
