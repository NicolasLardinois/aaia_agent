import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DeepDiveHeader } from "./DeepDiveHeader";
import { demoDeepDive } from "../../data/demo/deepdive";

describe("DeepDiveHeader", () => {
  it("zeigt Ticker, Name, beide Etiketten und Kurs/Markt", () => {
    render(<DeepDiveHeader view={demoDeepDive("GC=F")} />);
    expect(screen.getByText(/GC=F/)).toBeInTheDocument();
    expect(screen.getByText(/Gold/)).toBeInTheDocument();
    expect(screen.getByText("Edelmetall")).toBeInTheDocument(); // underlying-Badge
    expect(screen.getByText("Future")).toBeInTheDocument();     // wrapper-Badge
    expect(screen.getByText(/COMEX/)).toBeInTheDocument();
    expect(screen.getByText(/2380/)).toBeInTheDocument();
  });
  it("ruft onCompare beim Klick auf 'vergleichen'", () => {
    const onCompare = vi.fn();
    render(<DeepDiveHeader view={demoDeepDive("GC=F")} onCompare={onCompare} />);
    fireEvent.click(screen.getByRole("button", { name: /vergleichen/i }));
    expect(onCompare).toHaveBeenCalledOnce();
  });
  it("zeigt 'nicht verfügbar' wenn price null", () => {
    render(<DeepDiveHeader view={demoDeepDive("ZZZZ")} />);
    expect(screen.getByText(/nicht verfügbar/)).toBeInTheDocument();
  });
});
