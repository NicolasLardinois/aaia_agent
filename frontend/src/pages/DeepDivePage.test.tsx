import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route, Link } from "react-router-dom";
import { DeepDivePage } from "./DeepDivePage";
import { loadDeepDive } from "../data/deepdive";

vi.mock("echarts-for-react", () => ({ default: () => null }));

function renderAt(ticker: string) {
  return render(
    <MemoryRouter initialEntries={[`/deep-dive/${ticker}`]}>
      <Routes>
        <Route path="/deep-dive/:ticker" element={<DeepDivePage loader={loadDeepDive} />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("DeepDivePage", () => {
  it("equity (AAPL): Header, Long/Short-Panel, Anomalie, equity-Tabs, KEIN Futures-Tab", async () => {
    renderAt("AAPL");
    await waitFor(() => expect(screen.getByText(/Apple/)).toBeInTheDocument());
    expect(screen.getByText("LONG-LINSE")).toBeInTheDocument();
    expect(screen.getByText("SHORT-LINSE")).toBeInTheDocument();
    expect(screen.getByText(/Anomalie-Schwere/)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Bewertung/ })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /Futures/ })).not.toBeInTheDocument();
    expect(screen.getByText("Demo-Daten")).toBeInTheDocument();
  });
  it("zeigt den Kursverlauf-Abschnitt (Mangel #6) bei vorhandener Historie", async () => {
    renderAt("AAPL");
    await waitFor(() => expect(screen.getByText(/Apple/)).toBeInTheDocument());
    expect(screen.getByText("Kursverlauf")).toBeInTheDocument();
    // letzter Kurs == aktueller Kurs (Historie endet auf price)
    expect(screen.getByText(/232\.1 USD/)).toBeInTheDocument();
  });
  it("bond (TLT): bond-Tab statt equity-Tabs", async () => {
    renderAt("TLT");
    await waitFor(() => expect(screen.getByRole("tab", { name: /Anleihe/ })).toBeInTheDocument());
    expect(screen.queryByRole("tab", { name: /Qualität/ })).not.toBeInTheDocument();
  });
  it("Tab-Wechsel rendert den Qualität-Inhalt (Altman-Z)", async () => {
    renderAt("AAPL");
    await waitFor(() => screen.getByRole("tab", { name: /Qualität/ }));
    fireEvent.click(screen.getByRole("tab", { name: /Qualität/ }));
    // exakt: der InfoTip-Tooltip-Text beginnt mit "Altman-Z-Score…" -> Regex wäre mehrdeutig
    expect(screen.getByText("Altman-Z")).toBeInTheDocument();
  });
  it("Cockpit-Wind sichtbar bei CL=F (Öl-Rückenwind)", async () => {
    renderAt("CL=F");
    await waitFor(() => expect(screen.getByText(/Rohstoffe \(Öl\)/)).toBeInTheDocument());
  });
  it("nicht gefunden (ZZZZ): Hinweis statt Tabs", async () => {
    renderAt("ZZZZ");
    await waitFor(() => expect(screen.getByText(/nicht gefunden/i)).toBeInTheDocument());
  });
  it("future (GC=F): Futures-Tab vorhanden und rendert Terminkurve-Inhalt", async () => {
    renderAt("GC=F");
    await waitFor(() => screen.getByRole("tab", { name: /Futures/ }));
    fireEvent.click(screen.getByRole("tab", { name: /Futures/ }));
    expect(screen.getByText(/Roll-Yield/)).toBeInTheDocument();
  });
  it("Ticker-Wechsel mit aktivem, im neuen Tab-Set fehlendem Tab => kein Crash (Tab-Reset)", async () => {
    // Regression: gleiche Komponenten-Instanz bei /deep-dive/:ticker -> useState(active) ueberlebt
    // den Wechsel. AAPL hat "Qualität" (equity), TLT (bond) nicht. Ohne Absicherung wuerde der
    // alte Tab "quality" einen leeren equity-Block dereferenzieren (Crash). Erwartet: Fallback
    // auf den ersten gueltigen Tab ("Anleihe"), kein Absturz.
    render(
      <MemoryRouter initialEntries={["/deep-dive/AAPL"]}>
        <Link to="/deep-dive/TLT">zu-TLT</Link>
        <Routes>
          <Route path="/deep-dive/:ticker" element={<DeepDivePage loader={loadDeepDive} />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByRole("tab", { name: /Qualität/ }));
    fireEvent.click(screen.getByRole("tab", { name: /Qualität/ })); // active = "quality"
    fireEvent.click(screen.getByText("zu-TLT"));                    // Ticker -> TLT (bond)
    await waitFor(() => expect(screen.getByRole("tab", { name: /Anleihe/ })).toBeInTheDocument());
    expect(screen.queryByRole("tab", { name: /Qualität/ })).not.toBeInTheDocument();
  });
  it("kein 'vergleichen'-Button ohne sinnvolles Gegenstück (AAPL)", async () => {
    renderAt("AAPL");
    await waitFor(() => expect(screen.getByText(/Apple/)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /vergleichen/i })).not.toBeInTheDocument();
  });
  it("'vergleichen'-Button vorhanden bei Ticker mit Gegenstück (GC=F)", async () => {
    renderAt("GC=F");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /vergleichen/i })).toBeInTheDocument(),
    );
  });
  it("Vergleich: ?vergleich=4GLD zeigt CompareView mit beiden Tickern", async () => {
    render(
      <MemoryRouter initialEntries={["/deep-dive/GC=F?vergleich=4GLD"]}>
        <Routes><Route path="/deep-dive/:ticker" element={<DeepDivePage loader={loadDeepDive} />} /></Routes>
      </MemoryRouter>,
    );
    // Warten bis CompareView-Header sichtbar (zwei Hüllen ist eindeutig)
    await waitFor(() => expect(screen.getByText(/zwei Hüllen/i)).toBeInTheDocument());
    expect(screen.getByText("4GLD")).toBeInTheDocument();
    expect(screen.getByText(/kein Roll/i)).toBeInTheDocument();
  });
});
