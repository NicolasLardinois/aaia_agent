import type {
  PositionDTO, KlumpenWarningDTO, KlumpenDimension, ConcentrationLimits,
} from "../contract/portfolio";

// Default-Limits = Backend-Werte (portfolio_monitor_agent): Sektor 0.40, underlying/
// asset_class 0.60, Geographie/country 0.70. Begruendung: ab dieser Netto-Konzentration
// gilt das Risiko als Klumpen. Injizierbar -> Demo/echt koennen ueberschreiben.
export const DEFAULT_LIMITS: ConcentrationLimits = { sector: 0.40, underlying: 0.60, geography: 0.70 };

// Pro Dimension der Feldname auf der Position.
const FIELD: Record<KlumpenDimension, keyof PositionDTO> = {
  sector: "sector", underlying: "underlying", geography: "geography",
};

function pct(value: number): string {
  return `${Math.round(value * 100)} %`;
}

// Klumpen je Dimension: |Σ signiertes Exposure| / Brutto > Limit. Signiert, damit ein Hedge
// (Gegenposition) die Netto-Konzentration senkt (sonst Fehlalarm). Strikt groesser:
// genau auf dem Limit noch okay (lueckenlose Baender, AGENTS.md §2).
export function detectKlumpen(
  positions: PositionDTO[],
  limits: ConcentrationLimits = DEFAULT_LIMITS,
): KlumpenWarningDTO[] {
  const gross = positions.reduce((s, p) => s + p.sizePctNav, 0);
  if (gross === 0) return [];

  const warnings: KlumpenWarningDTO[] = [];
  for (const dimension of ["sector", "underlying", "geography"] as KlumpenDimension[]) {
    const limit = limits[dimension];
    const buckets = new Map<string, number>();
    for (const p of positions) {
      const name = String(p[FIELD[dimension]]);
      const signed = p.direction === "long" ? p.sizePctNav : -p.sizePctNav;
      buckets.set(name, (buckets.get(name) ?? 0) + signed);
    }
    for (const [name, net] of buckets) {
      const share = Math.abs(net) / gross;
      if (share > limit) {
        warnings.push({
          dimension, name, pct: Number(share.toFixed(4)), limit,
          message: `${name} ${pct(share)} (Limit ${pct(limit)})`,
        });
      }
    }
  }
  return warnings;
}
