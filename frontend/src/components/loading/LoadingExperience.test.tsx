import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { LoadingExperience, WISDOM_ROTATE_MS } from "./LoadingExperience";
import { MARKET_WISDOM } from "../../data/marketWisdom";
import type { CockpitEvent } from "../../api/cockpitSocket";

const ev = (type: string): CockpitEvent => ({ type, source: "x", payload: {}, run_id: "r" });

describe("LoadingExperience", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    // Erst Timer leeren, dann auf Echtzeit zurueck — verhindert, dass ein
    // Intervall-Callback nach den Assertions noch ein setState ausserhalb von act feuert.
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it("zeigt Spinner, Status-Rolle und die erste Weisheit", () => {
    const { container } = render(<LoadingExperience />);
    // role=status + aria-live -> Screenreader bekommt den Lade-Status mit
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(container.querySelector("svg")).not.toBeNull(); // Hexagon-Spinner
    expect(screen.getByText(MARKET_WISDOM[0].text)).toBeInTheDocument();
  });

  it("rotiert nach dem Intervall zur naechsten Weisheit", () => {
    render(<LoadingExperience />);
    expect(screen.getByText(MARKET_WISDOM[0].text)).toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(WISDOM_ROTATE_MS); });
    expect(screen.queryByText(MARKET_WISDOM[0].text)).not.toBeInTheDocument();
    expect(screen.getByText(MARKET_WISDOM[1].text)).toBeInTheDocument();
  });

  it("zeigt die Zahl abgeschlossener Analyse-Schritte aus den Events", () => {
    render(<LoadingExperience events={[ev("A"), ev("B"), ev("C")]} />);
    expect(screen.getByText(/3\b.*Schritte/i)).toBeInTheDocument();
  });

  it("nutzt einen optionalen Titel (z. B. fuer den ersten Seitenaufbau)", () => {
    render(<LoadingExperience title="Cockpit wird geladen" />);
    expect(screen.getByText("Cockpit wird geladen")).toBeInTheDocument();
  });
});
