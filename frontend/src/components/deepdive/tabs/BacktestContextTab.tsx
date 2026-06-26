import type { BacktestContextDTO } from "../../../contract/deepdive";
import { formatNumber } from "../../../lib/format";
import { UnavailableField } from "../../UnavailableField";
import { Icon } from "../../icons";

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
          <span className="font-medium">{formatNumber(ctx.hitRatePct)} %</span>
        )}{" "}
        ({formatNumber(ctx.sampleSize)} historische Calls)
      </div>
      {ctx.history.length === 0 ? (
        <p className="text-muted">Keine Einzel-Historie für diesen Ticker.</p>
      ) : (
        <ul>
          {ctx.history.map((h, i) => (
            <li key={i} className="flex items-center gap-1.5">
              {h.date}: {h.verdict}
              {h.correct ? (
                <Icon name="check" label="Treffer" className="h-3.5 w-3.5 text-bull" />
              ) : (
                <Icon name="cross" label="Fehlprognose" className="h-3.5 w-3.5 text-bear" />
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
