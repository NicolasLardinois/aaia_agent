// BacktestCard.tsx — eine Bereichs-Karte im Backtester (US31, Spec §7 Slice 5).
// Zeigt je Bereich (Top-Down/Bottom-Up/Judgment) die Trefferquote, Stichprobengroesse
// und die kumulierte Trefferkurve (LineCurve). Die Karte empfaengt bereits gefilterte
// Ergebnisse — die Seite (BacktesterPage) wendet filterResults + area-Filter an.
// WICHTIG: leere Stichprobe => "n.v.", NICHT "0 %" (UNAVAILABLE != 0, Spec §5.4).
import { hitRate, hitRateCurve, formatHitRate } from "../../lib/backtest";
import type { BacktestResult, BacktestArea } from "../../contract/backtest";
import { LineCurve } from "../charts/LineCurve";

export interface BacktestCardProps {
  area: BacktestArea;          // top_down / bottom_up / judgment
  results: BacktestResult[];   // BEREITS gefilterte Ergebnisse fuer genau diesen Bereich
}

// Menschenlesbare Titel und Kurztexte je Bereich (US31, Wireframe §4.10).
const AREA_LABEL: Record<BacktestArea, string> = {
  top_down: "Top-Down — Regime korrekt?",
  bottom_up: "Bottom-Up — dominantes Signal korrekt?",
  judgment: "Judgment — Urteil profitabel?",
};

export function BacktestCard({ area, results }: BacktestCardProps) {
  // Trefferquote und Stichprobengroesse aus den gefilterten Ergebnissen berechnen.
  // hitRate liefert rate:null bei n=0 (leere Stichprobe = "n.v.", nicht "0 %").
  const hr = hitRate(results);
  // Kumulierte Trefferquote ueber die Zeit; leere Menge => [] (keine Null-Linie).
  const curve = hitRateCurve(results);

  return (
    <div className="rounded-lg border border-line p-4">
      {/* Bereichs-Titel (z. B. "Top-Down — Regime korrekt?") */}
      <h3 className="text-base font-semibold">{AREA_LABEL[area]}</h3>

      {/* Pflicht-Beschriftung US31: klar als rueckblickende Treffsicherheit markieren */}
      <p className="mt-0.5 text-xs text-muted">
        Hätten die alten Calls Geld gebracht?
      </p>

      {/* Trefferquote + Stichprobengroesse */}
      <div className="mt-3 flex items-baseline gap-3">
        <span className="text-2xl font-bold">
          {/* formatHitRate: null => "n.v.", Zahl => "75 %" — eigener Formatter (nicht formatConfidence) */}
          {formatHitRate(hr.rate)}
        </span>
        <span className="text-sm text-muted">n = {hr.n}</span>
      </div>

      {/* Equity-/Trefferkurve oder n.v.-Hinweis */}
      <div className="mt-4">
        {curve.length > 0 ? (
          // LineCurve: kumulierte Trefferquote (%) ueber die Zeit (chronologisch sortiert).
          // Wiederverwendung der bestehenden Chart-Komponente (nicht duplizieren).
          <LineCurve
            series={[{ name: "Kumulierte Trefferquote (%)", points: curve }]}
            height={180}
          />
        ) : (
          // Leere Stichprobe nach Filter: dezenter Hinweis, keine Null-Linie (UNAVAILABLE != 0).
          <p className="text-sm text-muted">Keine Daten für diese Auswahl.</p>
        )}
      </div>
    </div>
  );
}
