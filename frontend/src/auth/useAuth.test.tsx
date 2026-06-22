import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAuth } from "./useAuth";

describe("useAuth", () => {
  beforeEach(() => localStorage.clear());

  it("startet ohne Token", () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.token).toBeNull();
  });

  it("login speichert das Token (auch in localStorage), logout entfernt es", () => {
    const { result } = renderHook(() => useAuth());
    act(() => result.current.login("geheim"));
    expect(result.current.token).toBe("geheim");
    expect(localStorage.getItem("aaia_token")).toBe("geheim");
    act(() => result.current.logout());
    expect(result.current.token).toBeNull();
    expect(localStorage.getItem("aaia_token")).toBeNull();
  });
});
