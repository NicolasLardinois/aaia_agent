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

  // net_beta in % NAV gegen die SYMMETRISCHE Schwelle (×100), strikt groesser im Betrag:
  // ein stark net-LONG Buch (positiv) ist bei Markt-Rueckgang gefaehrdet -> Index-Short/VIX;
  // ein stark net-SHORT Buch (negativ) ist bei Rally gefaehrdet -> Index-Long/Teil-Eindecken.
  // Beides ist "marktsensitiv". null => UNAVAILABLE: aus einem unbekannten Wert wird NICHT geraten.
  const nb = exposure.netBeta;
  if (nb !== null && Math.abs(nb) > NET_BETA_HEDGE_THRESHOLD * 100) {
    const longSkew = nb > 0;
    out.push({
      id: "net-beta",
      text: longSkew
        ? `net_beta ${nb.toFixed(0)} % senken → Index-Short (z. B. SPY) oder VIX-Hedge erwägen`
        : `net_beta ${nb.toFixed(0)} % (netto short) gegensteuern → Index-Long oder Teil-Eindecken erwägen`,
      rationale: `aktien-only |net_beta| über ${Math.round(NET_BETA_HEDGE_THRESHOLD * 100)} % NAV — Buch ist stark marktsensitiv (netto ${longSkew ? "long" : "short"})`,
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
