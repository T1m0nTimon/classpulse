import { useState } from "react";
import { useNavigate } from "react-router";
import { Logo } from "../components/ui";
import { useT } from "../i18n";

export default function Join() {
  const { t } = useT();
  const nav = useNavigate();
  const [code, setCode] = useState("");
  const clean = code.toUpperCase().replace(/[^A-Z0-9]/g, "");
  return (
    <main className="min-h-dvh flex items-center justify-center p-5">
      <form className="w-full max-w-sm text-center fade-in" onSubmit={(e) => { e.preventDefault(); if (clean.length >= 4) nav(`/j/${clean}`); }}>
        <div className="flex justify-center"><Logo size={64} /></div>
        <h1 className="text-3xl font-bold mt-4">{t("joinTitle")}</h1>
        <p className="muted mt-1 mb-6">{t("enterCode")}</p>
        <input className="field text-center text-3xl font-mono tracking-[.2em] !min-h-[72px] uppercase" autoFocus autoComplete="off" autoCorrect="off"
          autoCapitalize="characters" spellCheck={false} maxLength={10} value={code} onChange={(e) => setCode(e.target.value)} aria-label={t("code")} placeholder="ABC1234" />
        <button className="btn btn-primary w-full mt-4 text-lg" disabled={clean.length < 4}>{t("join")} →</button>
        <p className="text-sm muted mt-6">🔒 {t("anonymous")}</p>
      </form>
    </main>
  );
}
