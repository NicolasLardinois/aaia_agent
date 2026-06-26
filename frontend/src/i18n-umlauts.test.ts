import { describe, it, expect } from "vitest";

// ---------------------------------------------------------------------------
// Umlaut-Guard (Bug #1): In nutzersichtbaren Texten muessen echte Umlaute
// (ä/ö/ü) stehen, NICHT die ASCII-Ersatzschreibweise (ae/oe/ue).
//
// WICHTIG: Code-KOMMENTARE nutzen im Projekt bewusst ASCII-Umlaute (Konvention)
// — die bleiben. Dieser Guard prueft daher nur die String-/JSX-Textflaeche und
// blendet Kommentare vorher aus. Legitime ue-/ae-/oe-Woerter (z. B. "Quelle",
// "zuerst", "gegensteuern", "undervalued") stehen NICHT auf der Verbotsliste.
// ---------------------------------------------------------------------------

// Alle getrackten Quell-Dateien als Rohtext (vite ?raw -> string, kein node-Typ noetig).
const RAW = import.meta.glob("./**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

// Verbotene Teilstrings: ASCII-Umlaut-Ersatz, die NIE legitim sind (auch nicht als
// Teil eines laengeren Wortes). Bewusst NICHT enthalten: "steuer", "quelle", "zuer",
// "euer", "auer", "uel", "alue" (alles legitime ue/ae/oe-Sequenzen).
const FORBIDDEN = [
  "fuer", "ueber", "koenn", "muess", "duerf", "wuerd", "hoehe", "hoeher",
  "groesse", "groesser", "verfueg", "erfuell", "ausfuehr", "durchfuehr",
  "einfuehr", "unterstuetz", "beruecksicht", "ueberhitzt", "rueckgang",
  "rueckkauf", "kursrueck", "zurueck", "naechst", "maerkt", "laender",
  "qualitaet", "aktualitaet", "volatilitaet", "paritaet", "aktivitaet",
  "kapazitaet", "realitaet", "auffaell", "unterschaetz", "schaetz", "gueter",
  "daempf", "vollstaend", "tragfaeh", "faehig", "halbjaehr", "vierteljaehr",
  "jaehrlich", "taeglich", "woechentl", "rohoel", "moeglich", "noetig",
  "gemaess", "maessig", "schoen", "boerse", "vermoegen", "behoerd", "foerder",
  "bevoelker", "erklaer", "auswaehl", "bestaetig", "gebuehr", "gefaehr",
  "faellig", "gehoer", "stoer", "loesch", "loesung", "fruehe", "spaeter",
  "gueltig", "praemie", "taetig", "geschaeft", "gewaehr",
];

// Kommentare neutralisieren (Block /* */ und Zeile //), Zeilenstruktur erhalten.
function stripComments(src: string): string {
  let s = src.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "));
  s = s.replace(/(^|[^:])\/\/[^\n]*/g, (m, p1) => p1 + m.slice(p1.length).replace(/[^\n]/g, " "));
  return s;
}

// String-Literale + JSX-Text einer Zeile einsammeln (grob, aber ausreichend).
function surfaceOf(line: string): string {
  const out: string[] = [];
  for (const re of [
    /"([^"\\]|\\.)*"/g,
    /'([^'\\]|\\.)*'/g,
    /`([^`\\]|\\.)*`/g,
    />([^<>]*)</g,
    /^([^<>{}]*)</g,
    />([^<>{}]*)$/g,
  ]) {
    let m: RegExpExecArray | null;
    while ((m = re.exec(line))) out.push(m[0]);
  }
  return out.join(" ").toLowerCase();
}

describe("i18n: keine ASCII-Umlaute (ae/oe/ue) in nutzersichtbaren Texten (Bug #1)", () => {
  const files = Object.entries(RAW).filter(
    ([path]) => !/\.test\.|\.d\.ts$|i18n-umlauts/.test(path),
  );

  it("scant ueberhaupt Dateien (Selbsttest des Globs)", () => {
    expect(files.length).toBeGreaterThan(50);
  });

  it.each(files)("%s enthaelt keine ASCII-Umlaut-Ersatzschreibung", (_path, src) => {
    const offenders: string[] = [];
    stripComments(src as string)
      .split("\n")
      .forEach((line, i) => {
        const surface = surfaceOf(line);
        for (const bad of FORBIDDEN) {
          if (surface.includes(bad)) offenders.push(`Z${i + 1}: "${bad}" in »${line.trim().slice(0, 80)}«`);
        }
      });
    expect(offenders, `ASCII-Umlaute gefunden:\n${offenders.join("\n")}`).toEqual([]);
  });
});
