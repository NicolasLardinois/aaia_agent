import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOnboarding } from "./useOnboarding";

beforeEach(() => localStorage.clear());

describe("useOnboarding", () => {
  it("ist ohne Flag noch nicht gesehen", () => {
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.seen).toBe(false);
  });
  it("markSeen setzt das Flag dauerhaft", () => {
    const { result } = renderHook(() => useOnboarding());
    act(() => result.current.markSeen());
    expect(result.current.seen).toBe(true);
    expect(localStorage.getItem("aaia_onboarding_seen")).toBe("1");
  });
  it("liest ein bereits gesetztes Flag", () => {
    localStorage.setItem("aaia_onboarding_seen", "1");
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.seen).toBe(true);
  });
});
