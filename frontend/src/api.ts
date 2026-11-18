// Thin fetch wrapper. The custom header is the CSRF protection the server requires.

export class ApiError extends Error {
  constructor(public status: number, public code: string) {
    super(code);
  }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown; participant?: string } = {}): Promise<T> {
  const headers: Record<string, string> = { "X-Requested-With": "classpulse" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.participant) headers["X-Participant"] = opts.participant;
  let res: Response;
  try {
    res = await fetch(path, {
      method: opts.method ?? (opts.body !== undefined ? "POST" : "GET"),
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(0, "network");
  }
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : res.status === 422 ? "invalid" : "error";
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

/** localStorage that survives Safari private mode / blocked storage (falls back to memory). */
const mem = new Map<string, string>();
export const store = {
  get(k: string): string | null {
    try {
      return localStorage.getItem(k);
    } catch {
      return mem.get(k) ?? null;
    }
  },
  set(k: string, v: string) {
    try {
      localStorage.setItem(k, v);
    } catch {
      mem.set(k, v);
    }
  },
};

export type Kind = "poll" | "questions" | "ideas" | "music" | "quiz";
export type PollType = "single" | "multi" | "yesno" | "scale" | "text" | "ranking";

export interface Song { id: string; uri: string; name: string; artists: string; album: string; image: string | null; url: string | null; explicit: boolean }
export interface Item { id: string; text: string; song: Song | null; status: string; answer: string; votes: number; created_at: string; in_playlist?: boolean; voted?: boolean }
export interface QuizQ { text: string; options: string[]; correct: number[]; seconds: number }
export interface Activity {
  id: string; kind: Kind; title: string; is_open: boolean;
  poll_type?: PollType; options?: string[]; results_mode?: "live" | "after"; voted?: boolean;
  results?: { total: number; counts?: number[]; average?: number | null; points?: number[]; avg_rank?: (number | null)[]; texts?: string[] };
  moderation?: boolean; items?: Item[]; allow_explicit?: boolean; sync_spotify?: boolean; playlist_url?: string | null; spotify_error?: string | null;
  questions?: QuizQ[];
  question?: { index: number; count: number; text: string; options: string[]; seconds: number; remaining: number; correct?: number[] } | null;
  quiz?: { phase: string; current: number; per_question?: { answers: number; counts: number[]; correct_count: number }[]; top_scores: number[]; players: number; my_score?: number; my_rank?: number | null; my_answers?: Record<string, number> };
}
export interface ClassSession {
  id: string; title: string; code: string; status: "live" | "paused" | "ended"; created_at: string; expires_at: string;
  participants: number; activity_count: number; filter_level?: string; blocked_words?: string[]; allowed_words?: string[]; activities?: Activity[];
}
export interface Teacher { id: string; email: string; name: string; language: "de" | "en" }
export interface AppConfig { public_url: string | null; lan_url: string | null; spotify_enabled: boolean; registration: boolean; ai_filter: boolean }
