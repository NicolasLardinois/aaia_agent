import type { BacktestContextDTO } from "../../../contract/deepdive";
import { UnavailableField } from "../../UnavailableField";

// Backtester-Kontext fuer DIESEN Ticker (US21): wie treffsicher war das System hier bisher.
// Trefferquote null -> UNAVAILABLE (kein Backtest-Datum vorhanden).
export function BacktestContextTab({ ctx }: { ctx: BacktestContextDTO }) {
  return (
    <div className="space-y-2 text-sm">
      <div>
        Trefferquote:{" "}
        {ctx.hitRatePct === null ? (
          <UnavailableField reason="keine Backtest-Daten" />
        ) : (
          <span className="font-medium">{ctx.hitRatePct} %</span>
        )}{" "}
        ({ctx.sampleSize} historische Calls)
      </div>
      {ctx.history.length === 0 ? (
        <p className="text-slate-500">Keine Einzel-Historie für diesen Ticker.</p>
      ) : (
        <ul>
          {ctx.history.map((h, i) => (
            <li key={i}>
              {h.date}: {h.verdict} {h.correct ? "✓" : "✗"}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
