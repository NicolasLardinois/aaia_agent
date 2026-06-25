import { Link } from "react-router-dom";
import type { Domain } from "../lib/contract";
import { isUnavailable } from "../lib/display";
import { SignalBadge } from "./SignalBadge";
import { UnavailableField } from "./UnavailableField";

const LABELS: Record<Domain["key"], string> = {
  commodities: "Rohstoffe",
  sentiment: "Sentiment",
  yield_curve: "Zinskurve",
  sectors: "Sektoren",
};

// Key -> Route-Slug (yield_curve -> yield-curve, Rest 1:1).
const SLUGS: Record<Domain["key"], string> = {
  commodities: "commodities",
  sentiment: "sentiment",
  yield_curve: "yield-curve",
  sectors: "sectors",
};

// Jede Kachel verlinkt auf den Drilldown /cockpit/<slug> (B7).
// UNAVAILABLE-Kacheln sind trotzdem klickbar (Drilldown zeigt SourceHealth-Details).
export function DomainTile({ domain }: { domain: Domain }) {
  return (
    <Link
      to={`/cockpit/${SLUGS[domain.key]}`}
      className="block rounded-lg border border-line p-3 transition-colors hover:border-brand/40 hover:bg-surface-2"
    >
      <div className="text-xs uppercase tracking-wide text-muted">{LABELS[domain.key]}</div>
      <div className="mt-1">
        {isUnavailable(domain) ? <UnavailableField reason="Quelle ausgefallen" /> : <SignalBadge signal={domain.signal} />}
      </div>
    </Link>
  );
}
