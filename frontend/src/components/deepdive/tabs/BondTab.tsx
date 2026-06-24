import type { BondBlockDTO } from "../../../contract/deepdive";
import { durationRisk } from "../../../lib/duration";
import { formatNumber } from "../../../lib/format";
import { UnavailableField } from "../../UnavailableField";

// bond-Variante (US14): Duration (Zinsrisiko), Credit-Rating (Ausfallrisiko), Spread.
// Modified Duration = ungefaehre %-Kursaenderung je 1 %-Punkt Renditeaenderung.
export function BondTab({ block }: { block: BondBlockDTO }) {
  const risk = durationRisk(block.modifiedDuration);
  return (
    <div className="space-y-2 text-sm">
      <div>
        Modified Duration:{" "}
        {block.modifiedDuration === null ? (
          <UnavailableField reason="Duration nicht verfügbar" />
        ) : (
          <span className="font-medium">
            {formatNumber(block.modifiedDuration)} J · Risiko {risk.level} ({risk.note})
          </span>
        )}
      </div>
      <div>
        Credit-Rating:{" "}
        {block.creditRating === null ? (
          <UnavailableField />
        ) : (
          <span className="font-medium">{block.creditRating}</span>
        )}
      </div>
      <div>
        Spread:{" "}
        {block.spreadBps === null ? (
          <UnavailableField />
        ) : (
          <span className="font-medium">{formatNumber(block.spreadBps)} bps</span>
        )}
      </div>
    </div>
  );
}
