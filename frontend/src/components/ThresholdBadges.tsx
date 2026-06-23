import { confidenceFlags } from "../lib/judgment";

// Konfidenz <0.50 -> auto-HOLD (Konzept §2.3 / frontend_notes.md).
export function AutoHoldBadge({ confidence }: { confidence: number }) {
  if (!confidenceFlags(confidence).autoHold) return null;
  return (
    <span className="inline-block rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
      ⚠ &lt;0.50 → auto-HOLD
    </span>
  );
}

// Konfidenz <0.35 -> zusaetzlich Cash-Bias.
export function CashBiasBadge({ confidence }: { confidence: number }) {
  if (!confidenceFlags(confidence).cashBias) return null;
  return (
    <span className="inline-block rounded bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">
      &lt;0.35 → Cash-Bias
    </span>
  );
}
