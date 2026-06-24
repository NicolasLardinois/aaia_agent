import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SentimentDrilldown } from "./SentimentDrilldown";
import { demoSentiment } from "../../data/demo/cockpit";

const loader = () => Promise.resolve(demoSentiment());

function renderPage() {
  return render(
    <MemoryRouter>
      <SentimentDrilldown loader={loader} />
    </MemoryRouter>,
  );
}

describe("SentimentDrilldown", () => {
  it("zeigt VIX mit Wert 18.2 und NEUTRAL-Badge", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("VIX")).toBeInTheDocument());
    expect(screen.getByText("18.2")).toBeInTheDocument();
    expect(screen.getByText("NEUTRAL")).toBeInTheDocument();
  });

  it("zeigt Fear & Greed mit Wert 62 und BEARISH-Badge", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Fear & Greed")).toBeInTheDocument());
    expect(screen.getByText("62")).toBeInTheDocument();
    expect(screen.getByText("BEARISH")).toBeInTheDocument();
  });

  it("zeigt Demo-Badge", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Demo-Daten")).toBeInTheDocument());
  });

  it("zeigt Note-Texte", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/moderate Volatilit/i)).toBeInTheDocument());
    expect(screen.getByText(/leichte Gier/i)).toBeInTheDocument();
  });
});
