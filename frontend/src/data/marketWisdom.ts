// Inhalt + Rotationslogik fuer das Lade-Erlebnis waehrend der Cockpit-Analyse (#3).
// Bewusst eine REINE Daten-/Logik-Datei (keine React-/Timer-Abhaengigkeit): die
// Komponente rendert nur, die Auswahl ist hier testbar gekapselt.
//
// Inhaltliche Sorgfalt (AGENTS.md §3): zitierte Boersenweisheiten sind ihren
// Urhebern zugeordnet; bei zugeschriebenen Zitaten steht "(zugeschrieben)".
// Fun-Facts sind fachlich korrekt; etymologisch Unsicheres ist mit "angeblich"
// gekennzeichnet, statt es als gesicherte Tatsache auszugeben.

export type WisdomKind = "weisheit" | "fakt";

export interface Wisdom {
  text: string;
  /** Urheber/Quelle — nur bei zitierten Weisheiten gesetzt, nicht bei Fun-Facts. */
  author?: string;
  kind: WisdomKind;
}

export const MARKET_WISDOM: Wisdom[] = [
  // ── Boersenweisheiten (zitiert) ───────────────────────────────────────────
  { kind: "weisheit", author: "Warren Buffett",
    text: "Sei ängstlich, wenn andere gierig sind — und gierig, wenn andere ängstlich sind." },
  { kind: "weisheit", author: "Warren Buffett",
    text: "Kaufe nur, was du auch zehn Jahre halten würdest, wenn die Börse so lange schlösse." },
  { kind: "weisheit", author: "John Maynard Keynes",
    text: "Der Markt kann länger irrational bleiben, als du solvent bleiben kannst." },
  { kind: "weisheit", author: "André Kostolany",
    text: "An der Börse ist alles möglich — auch das Gegenteil." },
  { kind: "weisheit", author: "André Kostolany",
    text: "Wer gut essen will, kauft Aktien; wer gut schlafen will, kauft Anleihen." },
  { kind: "weisheit", author: "Harry Markowitz",
    text: "Diversifikation ist der einzige kostenlose Mittagstisch an der Börse." },
  { kind: "weisheit", author: "Benjamin Graham",
    text: "Mr. Market ist dein Diener, nicht dein Ratgeber — nutze seine Launen, folge ihnen nicht." },
  { kind: "weisheit", author: "Carl Mayer von Rothschild (zugeschrieben)",
    text: "Kaufen, wenn die Kanonen donnern; verkaufen, wenn die Violinen spielen." },
  { kind: "weisheit", author: "Börsenweisheit",
    text: "Hin und her macht Taschen leer." },
  { kind: "weisheit", author: "Börsenweisheit",
    text: "Politische Börsen haben kurze Beine." },
  { kind: "weisheit", author: "Börsenweisheit",
    text: "Greife nie in ein fallendes Messer." },
  { kind: "weisheit", author: "Börsenweisheit",
    text: "Gewinne laufen lassen, Verluste begrenzen." },
  { kind: "weisheit", author: "Börsenweisheit",
    text: "Zeit im Markt schlägt das Timing des Marktes." },

  // ── Finanz-Fun-Facts (fachlich korrekt) ───────────────────────────────────
  { kind: "fakt",
    text: "72er-Regel: 72 ÷ Jahresrendite ≈ Verdopplungszeit. Bei 7 % verdoppelt sich Kapital in rund 10 Jahren." },
  { kind: "fakt",
    text: "Die Amsterdamer Börse (1602, Aktien der Niederländischen Ostindien-Kompanie) gilt als älteste moderne Wertpapierbörse." },
  { kind: "fakt",
    text: "Bullen- und Bärenmarkt sind angeblich nach der Angriffsart der Tiere benannt: Der Bulle stößt nach oben, der Bär schlägt nach unten." },
  { kind: "fakt",
    text: "Ein Schwarzer Schwan ist ein extrem seltenes, kaum vorhersehbares Ereignis mit großer Wirkung (Nassim Taleb)." },
  { kind: "fakt",
    text: "Gold und Realzinsen bewegen sich oft gegenläufig: Steigen die Realzinsen, gerät der Goldpreis meist unter Druck." },
  { kind: "fakt",
    text: "Cost-Average-Effekt: Wer regelmäßig denselben Betrag anlegt, kauft bei tiefen Kursen automatisch mehr Anteile." },
  { kind: "fakt",
    text: "Blue Chips — Aktien großer, etablierter Unternehmen — sind nach den teuersten Spielmarken im Casino benannt." },
];

// Reine Rotations-Indexfunktion: naechster Eintrag, am Ende rund herum.
// Robust gegen leere/Einzel-Listen und Indizes ausserhalb des Bereichs
// (kein Modulo-durch-0, kein Sprung ins Leere).
export function nextWisdomIndex(current: number, total: number): number {
  if (total <= 1) return 0;
  const next = current + 1;
  return next >= total ? 0 : next;
}
