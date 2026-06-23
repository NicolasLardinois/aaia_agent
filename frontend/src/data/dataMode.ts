export type DataMode = "demo" | "real" | "auto";

// Liest den globalen Daten-Modus aus VITE_DATA_MODE; Default/Unbekannt => "auto".
export function resolveDataMode(env: string | undefined): DataMode {
  if (env === "demo" || env === "real" || env === "auto") return env;
  return "auto";
}
