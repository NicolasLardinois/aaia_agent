import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useView } from "./useView";

describe("useView", () => {
  it("Erfolg: loading wird false, data gesetzt", async () => {
    const loader = vi.fn(() => Promise.resolve({ ok: 1 }));
    const { result } = renderHook(() => useView(loader));

    // Anfangszustand: loading true
    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toEqual({ ok: 1 });
    expect(result.current.error).toBeNull();
  });

  it("Fehler: loader rejected -> error gesetzt, data null, loading false", async () => {
    const loader = vi.fn(() => Promise.reject(new Error("netzwerk-fehler")));
    const { result } = renderHook(() => useView(loader));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe("Daten nicht ladbar");
    expect(result.current.data).toBeNull();
  });

  it("Unmount vor Resolve: kein setState-Warning (cancelled greift)", async () => {
    let resolvePromise!: (v: { ok: number }) => void;
    const loader = vi.fn(
      () => new Promise<{ ok: number }>((res) => { resolvePromise = res; })
    );

    const { result, unmount } = renderHook(() => useView(loader));
    expect(result.current.loading).toBe(true);

    // Unmount vor dem Resolve
    unmount();

    // Resolve nach Unmount -- sollte keinen Warning/Fehler ausloesen
    await act(async () => {
      resolvePromise({ ok: 42 });
    });

    // Nach Unmount: data bleibt null (cancelled hat gegriffen)
    expect(result.current.data).toBeNull();
  });
});
