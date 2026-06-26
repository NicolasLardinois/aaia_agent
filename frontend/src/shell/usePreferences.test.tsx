import { describe, it, expect, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { usePreferences } from "./usePreferences";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("dark");
  delete document.documentElement.dataset.reduceMotion;
});

describe("usePreferences", () => {
  it("liefert die Defaults und einen Setter", () => {
    const { result } = renderHook(() => usePreferences());
    expect(result.current.prefs).toEqual({ theme: "system", motion: "system", startView: "/cockpit" });
  });

  it("setzt eine Präferenz, persistiert und wendet sie an", () => {
    const { result } = renderHook(() => usePreferences());
    act(() => result.current.set("theme", "dark"));
    expect(result.current.prefs.theme).toBe("dark");
    expect(localStorage.getItem("aaia_theme")).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("hält zwei Instanzen über den Event-Bus synchron", () => {
    const a = renderHook(() => usePreferences());
    const b = renderHook(() => usePreferences());
    act(() => a.result.current.set("startView", "/portfolio"));
    expect(b.result.current.prefs.startView).toBe("/portfolio"); // ohne eigene Aktion mitgezogen
  });
});
