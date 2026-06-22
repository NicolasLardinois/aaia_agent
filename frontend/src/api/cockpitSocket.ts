import type { CockpitOverview } from "../lib/contract";

export interface CockpitEvent {
  type: string;
  source: string;
  payload: Record<string, unknown>;
  timestamp?: string; // optional: das terminale CockpitResultReady traegt keinen timestamp
  run_id: string;
}

// Minimal-Interface eines WebSockets -> per Factory injizierbar (jsdom hat keinen WebSocket).
export interface WebSocketLike {
  onopen: (() => void) | null;
  onmessage: ((ev: { data: string }) => void) | null;
  onerror: (() => void) | null;
  onclose: (() => void) | null;
  close(): void;
}

export type WebSocketFactory = (url: string) => WebSocketLike;

export interface SocketHandlers {
  onOpen?: () => void;
  onEvent?: (e: CockpitEvent) => void;
  onResult?: (overview: CockpitOverview, e: CockpitEvent) => void;
  onError?: () => void;
  onClose?: () => void;
}

function wsUrl(base: string): string {
  return base.replace(/^http/, "ws") + "/ws/cockpit";
}

export function openCockpitSocket(
  base: string,
  handlers: SocketHandlers,
  factory: WebSocketFactory = (url) => new WebSocket(url) as unknown as WebSocketLike,
): WebSocketLike {
  const ws = factory(wsUrl(base));
  ws.onopen = () => handlers.onOpen?.();
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data) as CockpitEvent;
    handlers.onEvent?.(msg);
    if (msg.type === "CockpitResultReady") {
      handlers.onResult?.(msg.payload as unknown as CockpitOverview, msg);
    }
  };
  ws.onerror = () => handlers.onError?.();
  ws.onclose = () => handlers.onClose?.();
  return ws;
}
