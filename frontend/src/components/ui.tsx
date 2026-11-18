import { useEffect, useState, type ReactNode } from "react";
import { useT } from "../i18n";

export function Sheet({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);
  const { t } = useT();
  return (
    <div className="fixed inset-0 z-40 flex items-end sm:items-center justify-center bg-black/40 backdrop-blur-sm fade-in" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="card w-full sm:max-w-xl max-h-[92dvh] overflow-y-auto rounded-b-none sm:rounded-b-[1.25rem] p-5 sm:p-6"
        style={{ paddingBottom: "max(1.25rem, env(safe-area-inset-bottom))" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4 gap-3">
          <h2 className="text-xl font-bold">{title}</h2>
          <button className="btn btn-soft btn-sm" onClick={onClose}>{t("close")}</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Toast({ msg, kind = "ok", onDone }: { msg: string; kind?: "ok" | "bad"; onDone: () => void }) {
  useEffect(() => {
    const id = window.setTimeout(onDone, 3500);
    return () => window.clearTimeout(id);
  }, [msg, onDone]);
  return (
    <div role="status" className="fixed left-1/2 -translate-x-1/2 z-50 fade-in px-5 py-3 rounded-2xl text-white font-medium shadow-lg max-w-[92vw] text-center"
      style={{ bottom: "max(1.5rem, calc(env(safe-area-inset-bottom) + 1rem))", background: kind === "ok" ? "#1d1d1f" : "var(--color-bad)" }}>
      {msg}
    </div>
  );
}

export function useToast() {
  const [toast, setToast] = useState<{ msg: string; kind: "ok" | "bad" } | null>(null);
  const node = toast ? <Toast msg={toast.msg} kind={toast.kind} onDone={() => setToast(null)} /> : null;
  return { node, ok: (msg: string) => setToast({ msg, kind: "ok" }), bad: (msg: string) => setToast({ msg, kind: "bad" }) };
}

export function Bar({ label, value, total, highlight, suffix }: { label: string; value: number; total: number; highlight?: boolean; suffix?: string }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <div className="mb-2.5">
      <div className="flex justify-between text-sm mb-1 gap-3">
        <span className={`font-medium break-words min-w-0 ${highlight ? "text-[var(--color-ok)]" : ""}`}>{highlight ? "✓ " : ""}{label}</span>
        <span className="muted tabular-nums shrink-0">{suffix ?? `${value} · ${pct}%`}</span>
      </div>
      <div className="h-3 rounded-full bg-[var(--soft)] overflow-hidden">
        <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${pct}%`, background: highlight ? "var(--color-ok)" : "var(--color-accent)" }} />
      </div>
    </div>
  );
}

export const KIND_ICON: Record<string, string> = { poll: "📊", questions: "🙋", ideas: "💡", music: "🎵", quiz: "🏆" };

export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="flex flex-wrap gap-1 p-1 rounded-2xl bg-[var(--soft)]" role="radiogroup">
      {options.map((o) => (
        <button key={o.value} role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}
          className={`flex-1 min-h-[42px] px-3 rounded-xl text-sm font-semibold transition ${value === o.value ? "bg-[var(--card)] shadow-sm" : "muted"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="flex items-center justify-between gap-4 py-2 cursor-pointer select-none">
      <span>{label}</span>
      <button type="button" role="switch" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)}
        className={`relative w-[51px] h-[31px] shrink-0 rounded-full transition-colors ${checked ? "bg-[var(--color-ok)]" : "bg-[var(--line)]"}`}>
        <span className={`absolute top-[2px] left-[2px] w-[27px] h-[27px] rounded-full bg-white shadow transition-transform ${checked ? "translate-x-5" : ""}`} />
      </button>
    </label>
  );
}

export function Logo({ size = 32 }: { size?: number }) {
  return <img src="/icon.svg" width={size} height={size} alt="" className="rounded-[22%]" />;
}
