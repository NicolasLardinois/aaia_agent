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
    const fetchFn = ((_url: string, init?: { method?: string }) => {
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

  it("setzt phase error, wenn der Mount-Load fehlschlaegt", async () => {
    const fetchFn = fakeFetch({ "GET http://x/api/cockpit": { status: 500 } });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: makeFakeWs }));
    await waitFor(() => expect(result.current.phase).toBe("error"));
  });

  it("schliesst den WebSocket beim Unmount", async () => {
    const ws = makeFakeWs();
    const fetchFn = fakeFetch({ "GET http://x/api/cockpit": { status: 204 } });
    const { result, unmount } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    act(() => { result.current.startAnalysis(); });
    unmount();
    expect(ws.close).toHaveBeenCalled();
  });

  it("ruft onUnauthorized bei 401 statt einen generischen Fehler zu setzen", async () => {
    const fetchFn = (async () => ({ status: 401, ok: false, json: async () => undefined })) as unknown as typeof fetch;
    const onUnauthorized = vi.fn();
    const { result } = renderHook(() =>
      useCockpit({ base: "http://x", fetchFn, wsFactory: makeFakeWs, onUnauthorized }),
    );
    await waitFor(() => expect(onUnauthorized).toHaveBeenCalledOnce());
    expect(result.current.phase).not.toBe("error");
  });

  it("nimmt das terminale CockpitResultReady NICHT in die Live-Events auf", async () => {
    const ws = makeFakeWs();
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 202, body: { run_id: "r1" } },
    });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    act(() => { result.current.startAnalysis(); });
    act(() => { ws.onopen!(); });
    act(() => { ws.onmessage!({ data: JSON.stringify({ type: "MacroChiefReady", source: "m", payload: {}, timestamp: "t", run_id: "r1" }) }); });
    act(() => { ws.onmessage!({ data: JSON.stringify({ type: "CockpitResultReady", source: "run_manager", payload: overview, timestamp: "t", run_id: "r1" }) }); });
    expect(result.current.events.map((e) => e.type)).toEqual(["MacroChiefReady"]);
  });

  it("RunInProgressError (POST 409) laesst phase 'running' und setzt keinen Fehler", async () => {
    const ws = makeFakeWs();
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 409 },
    });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));

    act(() => { result.current.startAnalysis(); });
    act(() => { ws.onopen!(); });

    // Nach dem POST (409 = RunInProgressError) bleibt phase "running", kein Fehler.
    await waitFor(() => expect(result.current.phase).toBe("running"));
    expect(result.current.error).toBeNull();
  });

  it("UnauthorizedError bei startRun (POST 401) ruft onUnauthorized und setzt NICHT phase 'error'", async () => {
    const ws = makeFakeWs();
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 401 },
    });
    const onUnauthorized = vi.fn();
    const { result } = renderHook(() =>
      useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws, onUnauthorized }),
    );
    await waitFor(() => expect(result.current.phase).toBe("ready"));

    act(() => { result.current.startAnalysis(); });
    act(() => { ws.onopen!(); });

    await waitFor(() => expect(onUnauthorized).toHaveBeenCalled());
    expect(result.current.phase).not.toBe("error");
  });

  it("CockpitRunFailed -> phase error + Meldung aus dem Payload", async () => {
    const ws = makeFakeWs();
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 202, body: { run_id: "r1" } },
    });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    act(() => { result.current.startAnalysis(); });
    act(() => { ws.onopen!(); });
    act(() => { ws.onmessage!({ data: JSON.stringify({ type: "CockpitRunFailed", source: "run_manager", payload: { message: "Analyse fehlgeschlagen" }, run_id: "r1" }) }); });
    await waitFor(() => expect(result.current.phase).toBe("error"));
    expect(result.current.error).toBe("Analyse fehlgeschlagen");
  });

  it("CockpitRunFailed mit leerem Payload -> Fallback-Meldung", async () => {
    const ws = makeFakeWs();
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 202, body: { run_id: "r1" } },
    });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    act(() => { result.current.startAnalysis(); });
    act(() => { ws.onopen!(); });
    act(() => { ws.onmessage!({ data: JSON.stringify({ type: "CockpitRunFailed", source: "run_manager", payload: {}, run_id: "r1" }) }); });
    await waitFor(() => expect(result.current.phase).toBe("error"));
    expect(result.current.error).toBe("Analyse fehlgeschlagen");
  });

  it("unaufgeforderter onClose waehrend des Laufs -> phase error", async () => {
    const ws = makeFakeWs();
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 202, body: { run_id: "r1" } },
    });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    act(() => { result.current.startAnalysis(); });
    act(() => { ws.onopen!(); });
    act(() => { ws.onclose!(); });  // Kabel reisst, ohne Terminal
    await waitFor(() => expect(result.current.phase).toBe("error"));
    expect(result.current.error).toBe("Verbindung zum Server unterbrochen");
  });

  it("Guard: nach onResult ist onClose abgehaengt -> phase bleibt ready", async () => {
    const ws = makeFakeWs();
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 202, body: { run_id: "r1" } },
    });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    act(() => { result.current.startAnalysis(); });
    act(() => { ws.onopen!(); });
    act(() => { ws.onmessage!({ data: JSON.stringify({ type: "CockpitResultReady", source: "run_manager", payload: overview, timestamp: "t", run_id: "r1" }) }); });
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    expect(ws.onclose).toBeNull();          // Handler abgehaengt -> kein Fehlalarm moeglich
    expect(ws.onerror).toBeNull();
    expect(ws.close).toHaveBeenCalled();
  });

  it("Re-Run schliesst den alten Socket ohne Fehlalarm", async () => {
    const ws1 = makeFakeWs();
    const ws2 = makeFakeWs();
    const queue = [ws1, ws2];
    const factory = () => queue.shift()!;
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 202, body: { run_id: "r1" } },
    });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: factory }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    act(() => { result.current.startAnalysis(); });  // oeffnet ws1
    act(() => { result.current.startAnalysis(); });  // Re-Run: schliesst ws1, oeffnet ws2
    expect(ws1.onclose).toBeNull();          // alter Handler abgehaengt
    expect(ws1.onerror).toBeNull();
    expect(ws1.close).toHaveBeenCalled();
    expect(result.current.phase).toBe("running");
    expect(result.current.error).toBeNull();
  });
});
