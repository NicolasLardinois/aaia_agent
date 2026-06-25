import type { CommodityBlockDTO } from "../../../contract/deepdive";
import { formatNumber, formatSigned } from "../../../lib/format";
import { SignalBadge } from "../../SignalBadge";
import { UnavailableField } from "../../UnavailableField";

// commodity/precious-Variante (US16): Supply/Demand, Saisonalitaet, COT (kontraer) bzw.
// Cross-Metal-Ratios. COT-Index hoch => Spekulanten extrem long => kontraer bearish (cot_agent).
// null-Felder -> UNAVAILABLE (nie 0/neutral, Spec §5.4).
export function CommodityTab({ block }: { block: CommodityBlockDTO }) {
  return (
    <div className="space-y-3 text-sm">
      <div>
        Supply/Demand: <SignalBadge signal={block.supplyDemandSignal} />{" "}
        <span className="text-muted">— {block.supplyDemandNote}</span>
      </div>
      <div>
        <div className="text-xs uppercase text-muted">Saisonalität</div>
        {block.seasonality.length === 0 ? (
          <UnavailableField reason="Saisonalität nicht verfügbar" />
        ) : (
          <ul>
            {block.seasonality.map((s) => (
              <li key={s.month}>
                {s.month}: {formatSigned(s.avgReturnPct)} %
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        COT-Index:{" "}
        {block.cotIndex === null ? (
          <UnavailableField reason="COT nicht verfügbar" />
        ) : (
          <span className="font-medium">
            {formatNumber(block.cotIndex)}/100 · <SignalBadge signal={block.cotSignal} />{" "}
            <span className="text-xs text-muted">(konträr: hoher Index = bearish)</span>
          </span>
        )}
      </div>
      {block.crossMetal.length > 0 && (
        <div>
          <div className="text-xs uppercase text-muted">Cross-Metal-Ratios</div>
          <ul>
            {block.crossMetal.map((r) => (
              <li key={r.name}>
                {r.name}: <span className="font-medium">{formatNumber(r.value)}</span> — {r.note}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
