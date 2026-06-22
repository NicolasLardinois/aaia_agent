import { useCallback, useEffect, useRef, useState } from "react";
import { getCockpit, startRun } from "../api/client";
import { openCockpitSocket, type CockpitEvent, type WebSocketFactory, type WebSocketLike } from "../api/cockpitSocket";
import type { CockpitOverview } from "../lib/contract";

export type Phase = "loading" | "ready" | "running" | "error";

export interface UseCockpitDeps {
  base?: string;
  fetchFn?: typeof fetch;
  wsFactory?: WebSocketFactory;
}

export interface UseCockpit {
  overview: CockpitOverview | null;
  phase: Phase;
  events: CockpitEvent[];
  error: string | null;
  startAnalysis: () => void;
}

const DEFAULT_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export function useCockpit(deps: UseCockpitDeps = {}): UseCockpit {
  const base = deps.base ?? DEFAULT_BASE;
  const fetchFn = deps.fetchFn;
  const wsFactory = deps.wsFactory;

  const [overview, setOverview] = useState<CockpitOverview | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [events, setEvents] = useState<CockpitEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocketLike | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCockpit(base, fetchFn)
      .then((data) => { if (!cancelled) { setOverview(data); setPhase("ready"); } })
      .catch(() => { if (!cancelled) { setError("Backend nicht erreichbar"); setPhase("error"); } });
    return () => { cancelled = true; };
  }, [base, fetchFn]);

  // Offenen WebSocket beim Unmount schliessen (kein Leak / kein setState nach Unmount).
  useEffect(() => () => { wsRef.current?.close(); }, []);

  const startAnalysis = useCallback(() => {
    setPhase("running");
    setEvents([]);
    setError(null);
    wsRef.current?.close(); // evtl. vorherigen Lauf schliessen (z. B. Doppelklick)
    // Reihenfolge: erst WS oeffnen, POST erst in onOpen -> keine fruehen Events verloren.
    wsRef.current = openCockpitSocket(
      base,
      {
        onOpen: () => {
          startRun(base, fetchFn).catch(() => { setError("Start fehlgeschlagen"); setPhase("error"); });
        },
        // onEvent feuert fuer JEDE Nachricht; das terminale CockpitResultReady gehoert
        // nicht in den Fortschritts-Stream (es wird ueber onResult behandelt).
        onEvent: (e) => { if (e.type !== "CockpitResultReady") setEvents((prev) => [...prev, e]); },
        onResult: (ov) => { setOverview(ov); setPhase("ready"); wsRef.current?.close(); },
        onError: () => { setError("WebSocket-Fehler"); setPhase("error"); },
      },
      wsFactory,
    );
  }, [base, fetchFn, wsFactory]);

  return { overview, phase, events, error, startAnalysis };
}
