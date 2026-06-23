// Gemeinsame Abhaengigkeiten jeder Daten-Naht (injizierbar -> testbar gegen Fakes).
export interface ApiDeps {
  base?: string;
  fetchFn?: typeof fetch;
  token?: string | null;
}
