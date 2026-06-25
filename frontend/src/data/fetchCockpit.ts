// ECHTE Seite der Tausch-Naht (Spec §2): holt das letzte Cockpit-Ergebnis von /api/cockpit
// und mappt den durchgereichten detail.buffett-Block auf den Frontend-Vertrag BuffettView.
// Die Backend-Keys sind snake_case (API-Konvention) -> hier auf camelCase gemappt.
import type { ApiDeps } from "./apiDeps";
import type { BuffettView, BuffettCountry } from "../contract/cockpit";
import type { Signal } from "../lib/contract";

// Basis-URL wie in useCockpit: aus VITE_API_BASE_URL, sonst lokaler Default.
const DEFAULT_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

// Token wie von useAuth persistiert (localStorage["aaia_token"]). try/catch fuer
// Umgebungen ohne localStorage (defensiv).
function readToken(): string | null {
  try {
    return localStorage.getItem("aaia_token");
  } catch {
    return null;
  }
}

// Form der /api/cockpit-Antwort, soweit fuer den Buffett-Drilldown gebraucht.
interface BuffettCountryDTO {
  iso3: string;
  name: string;
  ratio_pct: number | null;
  signal: Signal;
  z_score: number | null;
  year: number | null;
  history: { year: number; ratio_pct: number }[];
}
interface CockpitDetailResponse {
  sources_active: number;
  sources_total: number;
  detail: { buffett: { global_median: number; countries: BuffettCountryDTO[] } };
}

function toCountry(dto: BuffettCountryDTO): BuffettCountry {
  return {
    iso3: dto.iso3,
    name: dto.name,
    ratioPct: dto.ratio_pct as number, // null-Ratio wird vorher herausgefiltert (s. fetchBuffett)
    signal: dto.signal,
    zScore: dto.z_score,
    year: dto.year,
    history: dto.history.map((h) => ({ year: h.year, ratioPct: h.ratio_pct })),
  };
}

export async function fetchBuffett(deps?: ApiDeps): Promise<BuffettView> {
  const base = deps?.base ?? DEFAULT_BASE;
  const fetchFn = deps?.fetchFn ?? fetch;
  const token = deps?.token ?? readToken();

  const res = await fetchFn(`${base}/api/cockpit`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  // 204 = noch kein Lauf -> es gibt nichts anzuzeigen (ehrlich als Fehler an useView).
  if (res.status === 204) {
    throw new Error("Noch keine Analyse — bitte zuerst im Cockpit eine Analyse starten.");
  }
  if (!res.ok) throw new Error(`GET /api/cockpit fehlgeschlagen: ${res.status}`);

  const payload = (await res.json()) as CockpitDetailResponse;
  const buffett = payload.detail.buffett;

  return {
    isDemo: false,
    sourcesActive: payload.sources_active,
    sourcesTotal: payload.sources_total,
    failed: [],
    globalMedian: buffett.global_median,
    analyzedIso3: "USA", // Default-Hervorhebung; spaeter aus dem market-Param ableitbar
    // Laender ohne Ratio koennen weder in Tabelle noch Karte gezeigt werden -> herausfiltern
    // (Vertrag: ratioPct ist number). UNAVAILABLE != 0: lieber weglassen als 0 erfinden.
    countries: buffett.countries.filter((c) => c.ratio_pct !== null).map(toCountry),
  };
}
