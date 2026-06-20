# Block F4a: Risiko-Kennzahlen — `net_beta` (pro Region) + Portfolio-Vola verdrahten — Design

**Datum:** 2026-06-20
**Status:** Genehmigt (Design)
**Teil von:** Shorts-Programm (`docs/short.md`; F4-Folgepunkt aus PR#7-Review, `docs/open_todos.md` Block #3). Erster Schritt der Risiko-Kennzahlen-Verfeinerung. Liefert die **richtungs-bewusste Markt-Exposure** (`net_beta`), die **3b (Track-B-Hedge)** zum Sizing braucht.

## Kontext & Ziel

3a führte `net_exposure = Σ long − Σ short` ein. Diese Skalarzahl verrechnet jeden Long- mit jedem Short-Dollar **unabhängig vom Markt-Beta** → als alleinige Hedge-Aussage irreführend (siehe Logbuch). Außerdem ist die im Monitor vorhandene **Portfolio-Vola** mangels `returns_provider` heute **nicht produktiv** (immer 0).

**Ziel:**
1. **`net_beta` pro Region** in den Monitor-Snapshot — beta-bereinigte, richtungs-bewusste Markt-Exposure **je Markt** (USA/CH/Eurozone), als **Geldbetrag** (Basiswährung) = direkte Hedge-Notional für 3b.
2. **`returns_provider` produktiv verdrahten** → die vorhandene Vola-/MaxDD-Rechnung wird live + korrelations-korrekt (Risiko-Magnitude, komplementär zu `net_beta`).

## Scope

**Im Block:**
- `net_beta` (dict `{region: $-Betrag}`) im Snapshot; Beta je Position via `market_provider.get_info(ticker)["beta"]`, fehlend/None → **1,0**. Werte FX-konvertiert (Basiswährung), Vorzeichen nach Richtung. Region aus `Position.country`. Optional `net_beta_pct` (vs. Brutto).
- `returns_provider` als Callable `ticker → Renditereihe` aus `get_price_history` verdrahten (`background_runner` + Monitor-Instanziierung) → Vola/MaxDD live.
- Anzeige (`net_beta` je Region) + Tests.

**Außerhalb (Folge-Schritte):**
- **ETF-Look-Through** (braucht Holdings-Quelle, `get_index_holdings` ist Stub) — nächster Block.
- **Kovarianz-/Korrelationsmatrix** statt Einzel-Beta — spätere Ausbaustufe.
- **3b** konsumiert `net_beta` (Hedge-Empfehlung) — späterer Block.

## Komponenten

### 1. `agents/portfolio/portfolio_monitor_agent.py` — `net_beta` pro Region
- **Region-Mapping** (Modul-Helper):
  ```python
  _CH = {"CH", "CHE", "Schweiz", "Switzerland"}
  _US = {"USA", "US", "United States"}
  _EUROZONE = {"DE","FR","IT","ES","NL","AT","BE","PT","FI","IE","GR","SK","SI","EE","LV","LT","LU","MT","CY",
               "Deutschland","Frankreich","Eurozone"}
  def _region_of(country: str) -> str:
      c = (country or "").strip()
      if c in _US: return "USA"
      if c in _CH: return "CH"
      if c in _EUROZONE: return "Eurozone"
      return c or "Unbekannt"
  ```
- **Beta je Position** (Methode, defensiv):
  ```python
  def _beta_for(self, ticker: str) -> float:
      if self.market_provider is None:
          return 1.0
      try:
          info = self.market_provider.get_info(ticker) or {}
          b = info.get("beta")
          return float(b) if b is not None else 1.0
      except Exception:
          return 1.0
  ```
- In `_evaluate_positions` (nach der `values`/long/short-Berechnung): `net_beta` aufsummieren:
  ```python
  net_beta: dict[str, float] = {}
  for p, val in zip(positions, values):
      signed = val if p.direction == "long" else -val
      region = _region_of(p.country)
      net_beta[region] = net_beta.get(region, 0.0) + signed * self._beta_for(p.ticker)
  net_beta = {r: round(v, 2) for r, v in net_beta.items()}
  net_beta_pct = {r: round(v / gross, 3) for r, v in net_beta.items()} if gross > 0 else {}
  ```
  Snapshot um `"net_beta": net_beta` und `"net_beta_pct": net_beta_pct` erweitern.
- `run()`: nach der Exposure-Ausgabe je Region eine Zeile drucken, z. B. `net-β USA: $-80'000 (−0,8× Brutto)`.

### 2. `returns_provider` verdrahten
- Helper (Monitor-Modul): `make_returns_provider(market_provider)` → Callable `ticker → list[float]`:
  ```python
  def make_returns_provider(market_provider):
      def _provider(ticker: str) -> list:
          try:
              hist = market_provider.get_price_history(ticker, "1y")
              close = hist["Close"].dropna()
              return close.pct_change().dropna().tolist()
          except Exception:
              return []
      return _provider
  ```
- **`background_runner.py`:** einen Markt-Provider instanziieren (z. B. `YahooFinanceProvider`) und an den Monitor geben:
  ```python
  market = YahooFinanceProvider()
  PortfolioMonitorAgent(memory, portfolio_port=JsonPortfolioProvider(),
                        market_provider=market,
                        returns_provider=make_returns_provider(market))
  ```
  (Damit ist `get_info` für Beta **und** `returns_provider` für Vola live; die vorhandene Vola-/MaxDD-Logik bleibt unverändert.)

## Datenfluss
`PortfolioMonitorAgent._evaluate_positions(positions)` → je Position FX-Wert + Beta (`market_provider.get_info`) → **`net_beta` je Region** (Σ signed·β) im Snapshot; parallel `returns_provider` → vorhandene **Vola/MaxDD** live. (3b liest später `net_beta` für die Hedge-Größe.)

## Fehlerbehandlung
- Beta fehlt/Provider None/Exception → **1,0** (Markt-Annahme).
- `returns_provider`-Fehler → `[]` (Vola bleibt 0 für den Titel, kein Crash).
- Kein `market_provider` injiziert → net_beta nutzt Beta 1,0 (degradiert, kein Crash).

## Tests (`tests/`)
- **`_region_of`**: USA/CH/Eurozone-Mapping; unbekannt → Land/„Unbekannt".
- **`net_beta`** (`test_portfolio_monitor` erweitern): Fake-`market_provider` mit `get_info` → Beta je Ticker. Beispiel **SPY long β1 / TSLA short β1.8, beide USA** → `net_beta["USA"] ≈ −80` (netto short Markt). Long-only High-Beta → `net_beta` > naivem Netto. Fehlendes Beta → 1,0. **Pro-Region-Trennung:** US- + CH-Position → zwei Einträge.
- **`make_returns_provider`**: Fake-`market_provider.get_price_history` (DataFrame mit „Close") → Renditeliste; Fehler → `[]`. Vola wird mit diesem Provider > 0 (vorhandener Vola-Test bestätigt die Mechanik).
- **Regression:** Gesamtsuite grün; Snapshot-Konsumenten (Memory-Save) brechen nicht durch die neuen Felder.

## Akzeptanzkriterien
1. Snapshot enthält `net_beta` (dict je Region, Geldbetrag) + `net_beta_pct`; signiert (long +, short −), beta-gewichtet, FX-konvertiert.
2. Beta via `market_provider.get_info`; fehlend → 1,0; defensiv (kein Crash).
3. Region-Gruppierung aus `Position.country` (USA/CH/Eurozone/…).
4. `returns_provider` produktiv verdrahtet → Portfolio-Vola/MaxDD live (nicht mehr konstant 0).
5. Anzeige zeigt `net_beta` je Region.
6. Gesamtsuite grün (0 failed).

## Review-Erweiterungen (PR #11, 2026-06-20)

Aus dem PR-#11-Review beschlossene Nachbesserungen (per TDD umgesetzt, Gesamtsuite 727 grün):

1. **`net_beta` nur Aktien/Indizes** (`_EQUITY_CLASSES = {"equity", "index"}`). `net_beta` dimensioniert einen **Aktien**-Index-Hedge (Track B); Bonds/Rohstoffe/Edelmetalle haben kein Aktienmarkt-Beta und gehören nicht hinein — ihr Risiko fängt die Vola ab. (Fehlendes Beta bei *Aktien* weiterhin → 1,0.)
2. **`net_beta_pct`-Nenner = Aktien-Brutto** derselben Region (nicht Gesamt-Brutto) → Zähler/Nenner gleiche Klasse („Äpfel mit Äpfeln"). Mischgröße (Zähler beta-gewichtet) bleibt, ist im Code dokumentiert.
3. **Vola per Datum statt per Listenposition.** `make_returns_provider` liefert eine **datierte `pandas.Series`**; die Vola führt die Renditen über den **gemeinsamen Datums-Index** zusammen (`DataFrame.dropna`) — sonst werden Titel mit verschieden langer/verschobener Historie (US/CH/EU-Feiertage) falsch übereinandergelegt.
4. **Parallele Daten-Beschaffung.** Neue `async _gather_market_data` holt Kurs/Beta/Renditen je Position parallel (`asyncio.to_thread` + `gather`); `_evaluate_positions` nimmt die vorab geholten Daten entgegen (Sync-Fallback für Direkt-Aufrufe). Vermeidet sequenzielles, rate-limit-anfälliges yfinance-I/O (AGENTS.md §2).
5. **Typisierung.** `market_provider: Optional[MarketDataProvider]` (Hexagonal: Abhängigkeit von der Port-Abstraktion sichtbar).
6. **Persistenz.** Risiko-Kennzahlen (`net_beta`, `net_beta_pct`, Exposure, Vola, MaxDD, HHI) werden als **`metrics`-jsonb** in `portfolio_snapshots` gespeichert und beim Laden ins Top-Level entpackt → 3b kann `net_beta` später aus dem Snapshot lesen. **Migration (vor Deploy einmalig):** `ALTER TABLE portfolio_snapshots ADD COLUMN metrics jsonb;`.

**Folge-Block (geparkt, eigenes Brainstorming):** instrumentengenaue **Nicht-Aktien-Hedges** (Bonds via DV01/Duration → Staatsanleihe-Futures; Rohstoffe je Underlying; Edelmetalle einzeln). DV01-Maschinerie (`core/utils/bond_math`) vorhanden, aber **Bond-Datenquelle** (`get_bond_data`) ist Stub → Voraussetzung. Siehe Logbuch.
