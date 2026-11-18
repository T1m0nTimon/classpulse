import type { Activity, Item } from "../api";
import { useT } from "../i18n";
import { Bar } from "./ui";

export function PollResults({ a, big = false }: { a: Activity; big?: boolean }) {
  const { t } = useT();
  const r = a.results;
  if (!r) return null;
  if (!r.total) return <p className="muted py-2">{t("noVotesYet")}</p>;
  const opts = a.options ?? [];
  const cls = big ? "text-xl" : "";
  if (a.poll_type === "scale") {
    const max = Math.max(...(r.counts ?? [0]), 1);
    return (
      <div className={cls}>
        <div className="text-3xl font-bold mb-3 tabular-nums">{t("average")}: {r.average}</div>
        <div className="flex items-end gap-1.5 h-32" aria-label={t("scale")}>
          {(r.counts ?? []).map((c, i) => (
            <div key={i} className="flex-1 flex flex-col items-center justify-end h-full gap-1">
              <span className="text-xs muted tabular-nums">{c || ""}</span>
              <div className="w-full rounded-t-lg bg-[var(--color-accent)] transition-[height] duration-500" style={{ height: `${(c / max) * 100}%`, minHeight: c ? 4 : 0 }} />
              <span className="text-xs font-semibold">{i + 1}</span>
            </div>
          ))}
        </div>
        <p className="muted text-sm mt-2">{r.total} {r.total === 1 ? t("vote") : t("votes")}</p>
      </div>
    );
  }
  if (a.poll_type === "text") {
    return (
      <div className={`flex flex-wrap gap-2 ${cls}`}>
        {r.texts?.map((x, i) => <span key={i} className="px-3 py-1.5 rounded-xl bg-[var(--soft)] break-words max-w-full">{x}</span>)}
      </div>
    );
  }
  if (a.poll_type === "ranking") {
    const pts = r.points ?? [];
    const order = opts.map((_, i) => i).sort((x, y) => pts[y] - pts[x]);
    const max = Math.max(...pts, 1);
    return (
      <div className={cls}>
        {order.map((i, pos) => (
          <Bar key={i} label={`${pos + 1}. ${opts[i]}`} value={pts[i]} total={max} suffix={`Ø ${r.avg_rank?.[i] ?? "–"}`} />
        ))}
        <p className="muted text-sm">{r.total} {r.total === 1 ? t("vote") : t("votes")}</p>
      </div>
    );
  }
  const counts = r.counts ?? [];
  const total = a.poll_type === "multi" ? r.total : counts.reduce((s, c) => s + c, 0);
  return (
    <div className={cls}>
      {opts.map((o, i) => <Bar key={i} label={o} value={counts[i] ?? 0} total={total} />)}
      <p className="muted text-sm">{r.total} {r.total === 1 ? t("vote") : t("votes")}</p>
    </div>
  );
}

export function SongLine({ item }: { item: Item }) {
  const s = item.song;
  if (!s) return <span className="font-medium break-words">{item.text}</span>;
  return (
    <div className="flex items-center gap-3 min-w-0">
      {s.image ? <img src={s.image} alt="" width={48} height={48} className="w-12 h-12 rounded-lg object-cover shrink-0" /> : <div className="w-12 h-12 rounded-lg bg-[var(--soft)] shrink-0" />}
      <div className="min-w-0">
        <div className="font-semibold truncate">{s.name}{s.explicit && <span className="pill bg-[var(--soft)] ml-1.5 !text-[10px]">E</span>}</div>
        <div className="muted text-sm truncate">{s.artists}</div>
      </div>
    </div>
  );
}

export function QuizBoard({ a, big = false }: { a: Activity; big?: boolean }) {
  const { t } = useT();
  const q = a.quiz;
  if (!q) return null;
  return (
    <div className={big ? "text-xl" : ""}>
      <div className="muted text-sm mb-2">{q.players} {t("players")}</div>
      {q.top_scores.length > 0 && (
        <>
          <div className="font-semibold mb-2">{t("topScores")}</div>
          <ol className="space-y-1">
            {q.top_scores.map((s, i) => (
              <li key={i} className="flex justify-between px-3 py-2 rounded-xl bg-[var(--soft)] tabular-nums">
                <span>{["🥇", "🥈", "🥉"][i] ?? `${i + 1}.`}</span><span className="font-semibold">{s} {t("points")}</span>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}

export function QuizQuestionResults({ a, big = false }: { a: Activity; big?: boolean }) {
  const { t } = useT();
  const q = a.question;
  const stats = q && a.quiz?.per_question?.[q.index];
  if (!q) return null;
  return (
    <div className={big ? "text-xl" : ""}>
      <div className="muted text-sm">{t("questionN", { n: q.index + 1, m: q.count })}</div>
      <div className="font-bold text-lg mb-3">{q.text}</div>
      {q.options.map((o, i) => (
        <Bar key={i} label={o} value={stats?.counts[i] ?? 0} total={stats?.answers ?? 0} highlight={q.correct?.includes(i)} />
      ))}
      <p className="muted text-sm">{stats?.answers ?? 0} {t("answers")}</p>
    </div>
  );
}
