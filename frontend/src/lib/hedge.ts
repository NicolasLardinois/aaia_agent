import type { ExposureDTO, KlumpenWarningDTO, HedgeSuggestionDTO } from "../contract/portfolio";

// Schwelle als benannte Konstante (kein magischer Wert): ab 30 % NAV beta-gewichtetem
// Aktien-Netto gilt das Buch als deutlich marktsensitiv -> Hedge erwaegen. Konservative,
// beratende Heuristik (Track B), keine harte Regel. Anteil 0..1; net_beta ist in % NAV.
export const NET_BETA_HEDGE_THRESHOLD = 0.30;

// Beratende Hedge-Vorschlaege (US26) — NIE ausfuehrend (US27). Abgeleitet aus Kennzahlen
// (net_beta) und Klumpen (Sektor). Jeder Vorschlag traegt eine rationale.
export function hedgeSuggestions(
  exposure: ExposureDTO,
  klumpen: KlumpenWarningDTO[],
): HedgeSuggestionDTO[] {
  const out: HedgeSuggestionDTO[] = [];

  // net_beta in % NAV gegen die als Anteil definierte Schwelle (×100) — strikt groesser.
  if (exposure.netBeta > NET_BETA_HEDGE_THRESHOLD * 100) {
    out.push({
      id: "net-beta",
      text: `net_beta ${exposure.netBeta.toFixed(0)} % senken → Index-Short (z. B. SPY) oder VIX-Hedge erwägen`,
      rationale: `aktien-only net_beta über ${Math.round(NET_BETA_HEDGE_THRESHOLD * 100)} % NAV — Buch ist marktsensitiv`,
    });
  }

  // Sektor-Klumpen -> Teilverkauf oder Sektor-Short der konzentrierten Branche.
  for (const k of klumpen.filter((w) => w.dimension === "sector")) {
    out.push({
      id: `sektor-${k.name}`,
      text: `${k.name}-Klumpen → Teilverkauf oder Sektor-Short erwägen`,
      rationale: k.message,
    });
  }
  return out;
}
