import { describe, it, expect, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useCockpit } from "./useCockpit";
import type { WebSocketLike } from "../api/cockpitSocket";

const overview = {
  regime: "Aufschwung", regime_confidence: 0.71, macro_status: "available",
  domains: [], sources_active: 5, sources_total: 5,
};

function fakeFetch(map: Record<string, { status: number; body?: unknown }>): typeof fetch {
  return (async (url: string, init?: { method?: string }) => {
    const key = `${init?.method ?? "GET"} ${url}`;
    const entry = map[key] ?? { status: 404 };
    return { status: entry.status, ok: entry.status >= 200 && entry.status < 300, json: async () => entry.body };
  }) as unknown as typeof fetch;
}

function makeFakeWs(): WebSocketLike {
  return { onopen: null, onmessage: null, onerror: null, onclose: null, close: vi.fn() };
}

describe("useCockpit", () => {
  it("laedt beim Mount die Uebersicht (200)", async () => {
    const fetchFn = fakeFetch({ "GET http://x/api/cockpit": { status: 200, body: overview } });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: makeFakeWs }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    expect(result.current.overview).toEqual(overview);
  });

  it("zeigt Leerzustand bei 204 (overview null, phase ready)", async () => {
    const fetchFn = fakeFetch({ "GET http://x/api/cockpit": { status: 204 } });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: makeFakeWs }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    expect(result.current.overview).toBeNull();
  });

  it("startet POST erst nach WS-onopen und fuellt beim Terminal die Uebersicht", async () => {
    const ws = makeFakeWs();
    const postSpy = vi.fn(async () => ({ status: 202, ok: true, json: async () => ({ run_id: "r1" }) }));
    const fetchFn = ((url: string, init?: { method?: string }) => {
      if ((init?.method ?? "GET") === "POST") return postSpy();
      return Promise.resolve({ status: 204, ok: false, json: async () => undefined });
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));

    act(() => { result.current.startAnalysis(); });
    expect(result.current.phase).toBe("running");
    // POST darf noch NICHT gelaufen sein (WS noch nicht offen):
    expect(postSpy).not.toHaveBeenCalled();

    act(() => { ws.onopen!(); });
    await waitFor(() => expect(postSpy).toHaveBeenCalledOnce());

    act(() => {
      ws.onmessage!({ data: JSON.stringify({ type: "CockpitResultReady", source: "run_manager", payload: overview, timestamp: "t", run_id: "r1" }) });
    });
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    expect(result.current.overview).toEqual(overview);
  });
});
