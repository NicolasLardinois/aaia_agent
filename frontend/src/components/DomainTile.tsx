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

export function DomainTile({ domain }: { domain: Domain }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <div className="text-xs uppercase tracking-wide text-slate-500">{LABELS[domain.key]}</div>
      <div className="mt-1">
        {isUnavailable(domain) ? <UnavailableField reason="Quelle ausgefallen" /> : <SignalBadge signal={domain.signal} />}
      </div>
    </div>
  );
}
