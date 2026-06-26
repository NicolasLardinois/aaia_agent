// ---- Regime-Deutung: Konjunkturphase -> Klartext + typische Anlageklassen ----
//
// Fachlicher Hintergrund (Konjunkturzyklus / "Investment Clock", Merrill Lynch 2004):
// Ueber den Zyklus rotiert die relative Staerke der Anlageklassen. Das Backend
// liefert eine von sechs Phasen (core/domain/models.py: MarketRegime) als deutschen
// String. Diese Funktion uebersetzt sie fuer Nutzer ohne Finanz-Vorwissen in:
//   - summary: was die Phase wirtschaftlich bedeutet
//   - favored: welche Anlageklassen historisch eher vorne liegen
//   - caution: worauf in dieser Phase zu achten ist
//
// WICHTIG (Datenrealitaet / AGENTS.md §3): Das sind *typische Tendenzen aus dem
// Lehrbuch-Zyklus*, kein Automatismus und kein Timing-Signal. Reihenfolge und
// Auspraegung variieren real stark — daher bewusst als Orientierung formuliert.

export interface RegimeInsight {
  /** Anzeige-Label der Phase (sauber gross geschrieben). */
  phase: string;
  summary: string;
  favored: string;
  caution: string;
  /** true, wenn das Regime einer bekannten Phase zugeordnet werden konnte. */
  known: boolean;
}

// Die sechs Phasen exakt wie das Backend sie emittiert (MarketRegime-Enum).
export const REGIME_KEYS = [
  "Boom",
  "Aufschwung",
  "Abschwung",
  "Rezession",
  "Erholung",
  "Depression",
] as const;

type RegimeKey = (typeof REGIME_KEYS)[number];

const TABLE: Record<RegimeKey, Omit<RegimeInsight, "known">> = {
  Boom: {
    phase: "Boom",
    summary:
      "Späte Expansion: Wachstum läuft heiss, Auslastung und Inflation steigen.",
    favored:
      "Rohstoffe und Substanz-/Value-Aktien profitieren vom Preisauftrieb.",
    caution:
      "Überhitzung und straffere Geldpolitik belasten vor allem Anleihen.",
  },
  Aufschwung: {
    phase: "Aufschwung",
    summary:
      "Wachstum zieht an, Inflation noch moderat — klassisch risikofreundliches Umfeld.",
    favored:
      "Aktien führen (vor allem zyklische und Wachstumswerte), Risiko-Appetit hoch.",
    caution:
      "Bewertungen können vorauslaufen; auf die beginnende Zinswende achten.",
  },
  Abschwung: {
    phase: "Abschwung",
    summary:
      "Das Wachstum hat den Höhepunkt überschritten und verliert an Tempo.",
    favored:
      "Defensive Sektoren und Qualitätstitel sind robuster als der Markt.",
    caution:
      "Zykliker und hoch bewertete Titel werden zunehmend anfällig.",
  },
  Rezession: {
    phase: "Rezession",
    summary:
      "Die Wirtschaft schrumpft, Unternehmensgewinne fallen, Notenbanken lockern oft.",
    favored:
      "Sichere Staatsanleihen und Cash sind defensiv im Vorteil.",
    caution:
      "Breiter Druck auf Aktien; Kredit- und Ausfallrisiken steigen.",
  },
  Erholung: {
    phase: "Erholung",
    summary:
      "Die Talsohle ist durchschritten, Frühindikatoren drehen nach oben.",
    favored:
      "Frühzykliker und Aktien drehen zuerst; Anleihen bleiben noch gestützt.",
    caution:
      "Die Erholung kann holprig sein — auf Bestätigung der Wende warten.",
  },
  Depression: {
    phase: "Depression",
    summary:
      "Tiefe, anhaltende Kontraktion mit breiter Risiko-Aversion am Markt.",
    favored:
      "Kapitalerhalt: Cash und erstklassige Staatsanleihen stehen vorn.",
    caution:
      "Liquidität und Bonität vor Rendite stellen; Risiko klein halten.",
  },
};

// Backend kann Gross-/Kleinschreibung oder Leerraum variieren -> normalisieren.
function normalize(regime: string): RegimeKey | null {
  const cleaned = regime.trim().toLowerCase();
  for (const key of REGIME_KEYS) {
    if (key.toLowerCase() === cleaned) return key;
  }
  return null;
}

export function regimeInsight(regime: string): RegimeInsight {
  const key = normalize(regime);
  if (key === null) {
    // Unbekanntes/leeres Regime: ehrlich bleiben, nichts erfinden.
    return {
      phase: regime.trim() || "Unbekannt",
      summary:
        "Für dieses Regime liegt keine hinterlegte Deutung vor. Bitte die Makro-Analyse für Details öffnen.",
      favored: "—",
      caution: "—",
      known: false,
    };
  }
  return { ...TABLE[key], known: true };
}
