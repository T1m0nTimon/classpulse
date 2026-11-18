import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { api, type ClassSession, type Kind, type Teacher } from "../api";
import { useApp } from "../App";
import { Creator, type ActivityBody } from "../components/Creator";
import { KIND_ICON, Logo, Segmented, Sheet, useToast } from "../components/ui";
import { useT, type Lang } from "../i18n";

export default function Home() {
  const { teacher } = useApp();
  return teacher ? <Dashboard teacher={teacher} /> : <Auth />;
}

function Auth() {
  const { t, err } = useT();
  const { setTeacher, config } = useApp();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { lang } = useT();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = mode === "login" ? { email, password } : { email, password, name, language: lang };
      setTeacher(await api<Teacher>(`/api/auth/${mode}`, { body }));
    } catch (e2) {
      setError(err(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center p-5">
      <div className="w-full max-w-md fade-in">
        <div className="flex flex-col items-center text-center mb-8">
          <Logo size={72} />
          <h1 className="text-4xl font-bold mt-4 tracking-tight">ClassPulse</h1>
          <p className="muted mt-2 text-lg">{t("tagline")}</p>
        </div>
        <form onSubmit={submit} className="card p-6 space-y-3">
          {mode === "register" && <input className="field" autoComplete="name" placeholder={t("name")} value={name} onChange={(e) => setName(e.target.value)} maxLength={80} />}
          <input className="field" type="email" autoComplete="email" inputMode="email" autoCapitalize="none" required placeholder={t("email")} value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="field" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={mode === "register" ? 8 : 1}
            placeholder={mode === "register" ? `${t("password")} – ${t("passwordHint")}` : t("password")} value={password} onChange={(e) => setPassword(e.target.value)} />
          {error && <p role="alert" className="text-[var(--color-bad)] text-sm">{error}</p>}
          <button className="btn btn-primary w-full text-lg" disabled={busy}>{mode === "login" ? t("login") : t("register")}</button>
          {(config?.registration ?? true) && (
            <button type="button" className="btn btn-soft w-full" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
              {mode === "login" ? t("noAccount") : t("haveAccount")}
            </button>
          )}
        </form>
        <div className="text-center mt-6"><Link to="/j" className="text-[var(--color-accent)] font-semibold">{t("forStudents")} →</Link></div>
        <LangSwitch className="mt-6" />
      </div>
    </main>
  );
}

function LangSwitch({ className = "", onChange }: { className?: string; onChange?: (l: Lang) => void }) {
  const { lang, setLang } = useT();
  return (
    <div className={`max-w-[220px] mx-auto ${className}`}>
      <Segmented value={lang} onChange={(l) => { setLang(l); onChange?.(l); }} options={[{ value: "de", label: "Deutsch" }, { value: "en", label: "English" }]} />
    </div>
  );
}

function greeting(t: ReturnType<typeof useT>["t"]) {
  const h = new Date().getHours();
  return h < 11 ? t("greetMorning") : h < 18 ? t("greetDay") : t("greetEvening");
}

function Dashboard({ teacher }: { teacher: Teacher }) {
  const { t, err } = useT();
  const nav = useNavigate();
  const toast = useToast();
  const [sessions, setSessions] = useState<ClassSession[] | null>(null);
  const [creating, setCreating] = useState<Kind | null>(null);
  const [settings, setSettings] = useState(false);
  const [spotifyConnected, setSpotifyConnected] = useState(false);

  useEffect(() => {
    api<ClassSession[]>("/api/sessions").then(setSessions).catch(() => setSessions([]));
    api("/api/spotify/status").then((s) => setSpotifyConnected(s.connected)).catch(() => {});
    const sp = new URLSearchParams(location.search).get("spotify");
    if (sp) {
      sp === "connected" ? toast.ok(t("spotifyConnectedMsg")) : toast.bad(t("spotifyErrorMsg"));
      history.replaceState(null, "", "/");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const newSession = async () => {
    try {
      const s = await api<ClassSession>("/api/sessions", { body: {} });
      nav(`/s/${s.id}`);
    } catch (e) {
      toast.bad(err(e));
    }
  };

  /** Two clicks: pick an activity, press Start → session + activity are created together. */
  const quickStart = async (body: ActivityBody) => {
    try {
      const s = await api<ClassSession>("/api/sessions", { body: { title: body.kind === "poll" ? "" : body.title } });
      await api(`/api/sessions/${s.id}/activities`, { body });
      nav(`/s/${s.id}`);
    } catch (e) {
      toast.bad(err(e));
    }
  };

  const quick: { kind: Kind; label: Parameters<typeof t>[0] }[] = [
    { kind: "poll", label: "startPoll" }, { kind: "questions", label: "startQuestions" }, { kind: "music", label: "startMusic" },
    { kind: "ideas", label: "startIdeas" }, { kind: "quiz", label: "startQuiz" },
  ];

  return (
    <main className="max-w-3xl mx-auto p-5 pb-16">
      <header className="flex items-center justify-between py-2 mb-6">
        <div className="flex items-center gap-2.5"><Logo /><span className="font-bold text-lg">ClassPulse</span></div>
        <button className="btn btn-soft btn-sm" onClick={() => setSettings(true)}>⚙︎ {t("settings")}</button>
      </header>

      <section className="fade-in">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">{greeting(t)}{teacher.name ? ` ${teacher.name}` : ""}</h1>
        <p className="text-xl muted mt-2">{t("homeQuestion")}</p>
        <button className="btn btn-primary w-full mt-6 text-xl min-h-[64px] rounded-[1.25rem]" onClick={newSession}>＋ {t("newSession")}</button>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4">
          {quick.map((q) => (
            <button key={q.kind} className="card p-4 text-left min-h-[96px] flex flex-col justify-between hover:ring-2 hover:ring-[var(--color-accent)] active:scale-[.98] transition" onClick={() => setCreating(q.kind)}>
              <span className="text-3xl" aria-hidden>{KIND_ICON[q.kind]}</span>
              <span className="font-semibold leading-tight">{t(q.label)}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-bold mb-3">{t("recentSessions")}</h2>
        {sessions && !sessions.length && <p className="muted">{t("noSessions")}</p>}
        <ul className="space-y-2">
          {sessions?.map((s) => (
            <li key={s.id}>
              <Link to={`/s/${s.id}`} className="card p-4 flex items-center gap-3 hover:ring-2 hover:ring-[var(--color-accent)] transition">
                <div className="flex-1 min-w-0">
                  <div className="font-semibold truncate">{s.title}</div>
                  <div className="text-sm muted">{new Date(s.created_at).toLocaleString()} · {s.activity_count} · <span className="font-mono">{s.code}</span></div>
                </div>
                <StatusPill status={s.status} />
              </Link>
            </li>
          ))}
        </ul>
      </section>

      {creating && <Creator kind={creating} spotify={spotifyConnected} onCancel={() => setCreating(null)} onCreate={quickStart} />}
      {settings && <AccountSettings teacher={teacher} onClose={() => setSettings(false)} />}
      {toast.node}
    </main>
  );
}

export function StatusPill({ status }: { status: string }) {
  const { t } = useT();
  const color = status === "live" ? "var(--color-ok)" : status === "paused" ? "var(--color-warn)" : "var(--muted)";
  return <span className="pill shrink-0" style={{ color, background: `color-mix(in srgb, ${color} 14%, transparent)` }}>● {t(status as "live")}</span>;
}

function AccountSettings({ teacher, onClose }: { teacher: Teacher; onClose: () => void }) {
  const { t, err } = useT();
  const { setTeacher, config } = useApp();
  const [sp, setSp] = useState<{ enabled: boolean; connected: boolean; display_name: string | null } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api("/api/spotify/status").then(setSp).catch(() => {}); }, []);

  const logout = async () => { await api("/api/auth/logout", { method: "POST" }).catch(() => {}); setTeacher(null); };
  const del = async () => {
    if (!confirm(t("confirmDeleteAccount"))) return;
    try { await api("/api/auth/me", { method: "DELETE" }); setTeacher(null); } catch (e) { setError(err(e)); }
  };
  const saveLang = (language: Lang) => api<Teacher>("/api/auth/me", { method: "PATCH", body: { language } }).then(setTeacher).catch(() => {});

  return (
    <Sheet title={t("settings")} onClose={onClose}>
      <div className="space-y-6">
        <section>
          <h3 className="font-semibold mb-2">{t("language")}</h3>
          <LangSwitch className="!mx-0" onChange={saveLang} />
        </section>
        <section>
          <h3 className="font-semibold mb-1">🎵 {t("spotify")}</h3>
          {!config?.spotify_enabled ? <p className="muted text-sm">{t("spotifyNotConfigured")}</p>
            : sp?.connected ? (
              <div className="flex items-center gap-3 flex-wrap">
                <span>{t("spotifyConnected")} <b>{sp.display_name}</b></span>
                <button className="btn btn-soft btn-sm" onClick={() => api("/api/spotify/disconnect", { method: "POST" }).then(() => setSp({ ...sp, connected: false }))}>{t("spotifyDisconnect")}</button>
              </div>
            ) : (
              <>
                <p className="muted text-sm mb-2">{t("spotifyHelp")}</p>
                {/* full page navigation: Spotify's login must not run in a popup (blocked on iOS) */}
                <a className="btn btn-primary" href="/api/spotify/login" style={{ background: "#1db954" }}>{t("spotifyConnect")}</a>
              </>
            )}
        </section>
        <section>
          <h3 className="font-semibold mb-2">{t("account")}</h3>
          <p className="muted text-sm mb-3">{teacher.email}</p>
          <p className="text-sm mb-3">🔒 {t("privacyNote")}</p>
          <div className="flex gap-2 flex-wrap">
            <button className="btn btn-soft" onClick={logout}>{t("logout")}</button>
            <button className="btn btn-danger" onClick={del}>{t("deleteAccount")}</button>
          </div>
          {error && <p className="text-[var(--color-bad)] text-sm mt-2">{error}</p>}
        </section>
      </div>
    </Sheet>
  );
}
