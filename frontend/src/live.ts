import { useEffect, useRef, useState } from "react";

/**
 * WebSocket with automatic reconnect. iOS Safari silently kills sockets when the iPad/iPhone sleeps
 * or the tab goes to the background, so we reconnect (and refetch) on visibilitychange/pageshow/online.
 */
export function useLive(path: string | null, onEvent: (e: any) => void, onReconnect: () => void) {
  const [connected, setConnected] = useState(true);
  const handler = useRef(onEvent);
  const reconnect = useRef(onReconnect);
  handler.current = onEvent;
  reconnect.current = onReconnect;

  useEffect(() => {
    if (!path) return;
    let ws: WebSocket | null = null;
    let closed = false;
    let retry = 0;
    let timer: number | undefined;
    let ping: number | undefined;

    const connect = () => {
      if (closed) return;
      const proto = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${location.host}${path}`);
      ws.onopen = () => {
        if (retry > 0) reconnect.current();
        retry = 0;
        setConnected(true);
        ping = window.setInterval(() => ws?.readyState === 1 && ws.send("ping"), 25000);
      };
      ws.onmessage = (m) => {
        try {
          handler.current(JSON.parse(m.data));
        } catch {
          /* ignore */
        }
      };
      ws.onclose = (e) => {
        window.clearInterval(ping);
        if (closed || e.code === 4404 || e.code === 4401 || e.code === 4403) return;
        setConnected(false);
        retry++;
        timer = window.setTimeout(connect, Math.min(10000, 500 * 2 ** retry));
      };
    };

    const wake = () => {
      if (document.visibilityState !== "visible") return;
      if (!ws || ws.readyState > 1) {
        window.clearTimeout(timer);
        retry = Math.max(retry, 1);
        connect();
      } else {
        reconnect.current(); // socket survived, but we may have missed events while asleep
      }
    };
    connect();
    document.addEventListener("visibilitychange", wake);
    window.addEventListener("pageshow", wake);
    window.addEventListener("online", wake);
    return () => {
      closed = true;
      window.clearTimeout(timer);
      window.clearInterval(ping);
      document.removeEventListener("visibilitychange", wake);
      window.removeEventListener("pageshow", wake);
      window.removeEventListener("online", wake);
      ws?.close();
    };
  }, [path]);

  return connected;
}

/** Coalesce bursts of "changed" events (30 students voting at once) into one refetch. */
export function useThrottled(fn: () => void, ms = 400) {
  const t = useRef<number | undefined>(undefined);
  const f = useRef(fn);
  f.current = fn;
  return () => {
    if (t.current) return;
    t.current = window.setTimeout(() => {
      t.current = undefined;
      f.current();
    }, ms);
  };
}
