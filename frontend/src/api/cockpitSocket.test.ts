import { describe, it, expect, vi } from "vitest";
import { openCockpitSocket, type WebSocketLike } from "./cockpitSocket";

function fakeWs(): WebSocketLike {
  return { onopen: null, onmessage: null, onerror: null, onclose: null, close: vi.fn() };
}

describe("openCockpitSocket", () => {
  it("leitet die ws-URL aus der http-Basis ab", () => {
    let seen = "";
    const ws = fakeWs();
    openCockpitSocket("http://127.0.0.1:8000", {}, (url) => { seen = url; return ws; });
    expect(seen).toBe("ws://127.0.0.1:8000/ws/cockpit");
  });

  it("ruft onOpen, onEvent und (beim Terminal) onResult", () => {
    const ws = fakeWs();
    const onOpen = vi.fn();
    const onEvent = vi.fn();
    const onResult = vi.fn();
    openCockpitSocket("https://api.example.com", { onOpen, onEvent, onResult }, () => ws);

    ws.onopen!();
    ws.onmessage!({ data: JSON.stringify({ type: "MacroChiefReady", source: "m", payload: {}, timestamp: "t", run_id: "r" }) });
    const ovPayload = { regime: "X", regime_confidence: 0.5, macro_status: "available", domains: [], sources_active: 5, sources_total: 5 };
    ws.onmessage!({ data: JSON.stringify({ type: "CockpitResultReady", source: "run_manager", payload: ovPayload, timestamp: "t", run_id: "r" }) });

    expect(onOpen).toHaveBeenCalledOnce();
    expect(onEvent).toHaveBeenCalledTimes(2);
    expect(onResult).toHaveBeenCalledOnce();
    expect(onResult).toHaveBeenCalledWith(ovPayload, expect.objectContaining({ type: "CockpitResultReady" }));
  });

  it("ruft onError und onClose", () => {
    const ws = fakeWs();
    const onError = vi.fn();
    const onClose = vi.fn();
    openCockpitSocket("http://x", { onError, onClose }, () => ws);
    ws.onerror!();
    ws.onclose!();
    expect(onError).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });
});
