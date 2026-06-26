import type { BuffettCountry } from "../contract/cockpit";
import type { MapPoint } from "../components/charts/ChoroplethMap";
import { zScoreFlag } from "./anomaly";

// GeoJSON (frontend/public/world.geo.json) traegt nur ENGLISCHE Laendernamen (Natural-Earth-
// Kurzformen), kein ISO-Property. Das Backend (Weltbank) liefert dagegen DUTZENDE Laender per
// iso3 + Weltbank-Klarname — und der weicht oft vom GeoJSON-Namen ab ("Russian Federation" vs
// "Russia", "Korea, Rep." vs "Korea", "Egypt, Arab Rep." vs "Egypt", "Czechia" vs "Czech Rep.").
// Damit buildMapOption() die Laender per nameProperty:"name" findet, mappt diese Tabelle iso3
// (stabiler Schluessel = Weltbank-Key) -> EXAKTEN GeoJSON-Namen. Ohne vollstaendige Tabelle
// blieb der grosse Rest der Welt WEISS (Bug #7). Der Konsistenz-Test in buffett.test.ts stellt
// sicher, dass jeder Wert ein real existierender Feature-Name in world.geo.json ist.
// Erweitern: neuen iso3-Eintrag ergaenzen (Wert = exakter name in world.geo.json).
export const ISO3_TO_MAP_NAME: Record<string, string> = {
  AFG: "Afghanistan", ALB: "Albania", DZA: "Algeria", AND: "Andorra", AGO: "Angola",
  ATG: "Antigua and Barb.", ARG: "Argentina", ARM: "Armenia", AUS: "Australia", AUT: "Austria",
  AZE: "Azerbaijan", BHS: "Bahamas", BHR: "Bahrain", BGD: "Bangladesh", BRB: "Barbados",
  BLR: "Belarus", BEL: "Belgium", BLZ: "Belize", BEN: "Benin", BTN: "Bhutan", BOL: "Bolivia",
  BIH: "Bosnia and Herz.", BWA: "Botswana", BRA: "Brazil", BRN: "Brunei", BGR: "Bulgaria",
  BFA: "Burkina Faso", BDI: "Burundi", KHM: "Cambodia", CMR: "Cameroon", CAN: "Canada",
  CPV: "Cape Verde", CAF: "Central African Rep.", TCD: "Chad", CHL: "Chile", CHN: "China",
  COL: "Colombia", COM: "Comoros", COG: "Congo", COD: "Dem. Rep. Congo", CRI: "Costa Rica",
  HRV: "Croatia", CUB: "Cuba", CYP: "Cyprus", CZE: "Czech Rep.", CIV: "Côte d'Ivoire",
  PRK: "Dem. Rep. Korea", DNK: "Denmark", DJI: "Djibouti", DMA: "Dominica", DOM: "Dominican Rep.",
  ECU: "Ecuador", EGY: "Egypt", SLV: "El Salvador", GNQ: "Eq. Guinea", ERI: "Eritrea",
  EST: "Estonia", ETH: "Ethiopia", FJI: "Fiji", FIN: "Finland", FRA: "France", GAB: "Gabon",
  GMB: "Gambia", GEO: "Georgia", DEU: "Germany", GHA: "Ghana", GRC: "Greece", GRL: "Greenland",
  GRD: "Grenada", GTM: "Guatemala", GIN: "Guinea", GNB: "Guinea-Bissau", GUY: "Guyana",
  HTI: "Haiti", HND: "Honduras", HUN: "Hungary", ISL: "Iceland", IND: "India", IDN: "Indonesia",
  IRN: "Iran", IRQ: "Iraq", IRL: "Ireland", ISR: "Israel", ITA: "Italy", JAM: "Jamaica",
  JPN: "Japan", JOR: "Jordan", KAZ: "Kazakhstan", KEN: "Kenya", KIR: "Kiribati", KOR: "Korea",
  KWT: "Kuwait", KGZ: "Kyrgyzstan", LAO: "Lao PDR", LVA: "Latvia", LBN: "Lebanon", LSO: "Lesotho",
  LBR: "Liberia", LBY: "Libya", LIE: "Liechtenstein", LTU: "Lithuania", LUX: "Luxembourg",
  MKD: "Macedonia", MDG: "Madagascar", MWI: "Malawi", MYS: "Malaysia", MLI: "Mali", MLT: "Malta",
  MRT: "Mauritania", MUS: "Mauritius", MEX: "Mexico", FSM: "Micronesia", MDA: "Moldova",
  MNG: "Mongolia", MNE: "Montenegro", MAR: "Morocco", MOZ: "Mozambique", MMR: "Myanmar",
  NAM: "Namibia", NPL: "Nepal", NLD: "Netherlands", NZL: "New Zealand", NIC: "Nicaragua",
  NER: "Niger", NGA: "Nigeria", NOR: "Norway", OMN: "Oman", PAK: "Pakistan", PLW: "Palau",
  PSE: "Palestine", PAN: "Panama", PNG: "Papua New Guinea", PRY: "Paraguay", PER: "Peru",
  PHL: "Philippines", POL: "Poland", PRT: "Portugal", QAT: "Qatar", ROU: "Romania", RUS: "Russia",
  RWA: "Rwanda", WSM: "Samoa", SAU: "Saudi Arabia", SEN: "Senegal", SRB: "Serbia",
  SYC: "Seychelles", SLE: "Sierra Leone", SGP: "Singapore", SVK: "Slovakia", SVN: "Slovenia",
  SLB: "Solomon Is.", SOM: "Somalia", ZAF: "South Africa", SSD: "S. Sudan", ESP: "Spain",
  LKA: "Sri Lanka", LCA: "Saint Lucia", VCT: "St. Vin. and Gren.", SDN: "Sudan", SUR: "Suriname",
  SWZ: "Swaziland", SWE: "Sweden", CHE: "Switzerland", SYR: "Syria", STP: "São Tomé and Principe",
  TJK: "Tajikistan", TZA: "Tanzania", THA: "Thailand", TLS: "Timor-Leste", TGO: "Togo",
  TON: "Tonga", TTO: "Trinidad and Tobago", TUN: "Tunisia", TUR: "Turkey", TKM: "Turkmenistan",
  UGA: "Uganda", UKR: "Ukraine", ARE: "United Arab Emirates", GBR: "United Kingdom",
  USA: "United States", URY: "Uruguay", UZB: "Uzbekistan", VUT: "Vanuatu", VEN: "Venezuela",
  VNM: "Vietnam", ESH: "W. Sahara", YEM: "Yemen", ZMB: "Zambia", ZWE: "Zimbabwe",
};

// Wandelt BuffettCountry-Eintraege in MapPoints fuer ChoroplethMap um.
// Neue Laender: ISO3_TO_MAP_NAME ergaenzen (Wert = exakter name in world.geo.json).
export function toMapPoints(countries: BuffettCountry[]): MapPoint[] {
  return countries.map((c) => ({
    iso3: c.iso3,
    name: ISO3_TO_MAP_NAME[c.iso3] ?? c.name, // Fallback: behalte deutschen Namen
    value: c.ratioPct,
    signal: c.signal,
  }));
}

export type SortKey = "ratioPct" | "zScore" | "name";

// Stabile Sortierung; null-zScore ans Ende (defensiv, Spec §6 / Datenrealitaet).
export function sortRows(rows: BuffettCountry[], key: SortKey, dir: "asc" | "desc"): BuffettCountry[] {
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    if (key === "name") return sign * a.name.localeCompare(b.name);
    const av = key === "zScore" ? a.zScore : a.ratioPct;
    const bv = key === "zScore" ? b.zScore : b.ratioPct;
    if (av === null) return 1;   // null immer ans Ende
    if (bv === null) return -1;
    return sign * (av - bv);
  });
}

export interface BuffettFilters { onlyZOutlier: boolean; onlyBearish: boolean }

// Filter (Konzept §4.3): nur Z-Ausreisser (|Z|>=1.5 -> zScoreFlag !== "none") und/oder nur BEARISH.
export function filterRows(rows: BuffettCountry[], f: BuffettFilters): BuffettCountry[] {
  return rows.filter((r) => {
    if (f.onlyZOutlier && (r.zScore === null || zScoreFlag(r.zScore) === "none")) return false;
    if (f.onlyBearish && r.signal !== "bearish") return false;
    return true;
  });
}

// vs. Median: Verhaeltnis + Wort. Median<=0 defensiv -> ratio 0.
// Lückenlose Bänder: [0.95, 1.05] -> "≈ am Median" (praktisch am Median)
export function vsMedianLabel(ratioPct: number, median: number): { label: string; ratio: number } {
  if (median <= 0) return { label: "—", ratio: 0 };
  const ratio = ratioPct / median;
  let label: string;
  if (ratio >= 1.5) label = "deutlich >";
  else if (ratio > 1.05) label = ">";
  else if (ratio >= 0.95) label = "≈ am Median"; // ratio in [0.95, 1.05] -> praktisch am Median
  else if (ratio < 0.67) label = "deutlich <";
  else label = "<";
  return { label, ratio };
}
