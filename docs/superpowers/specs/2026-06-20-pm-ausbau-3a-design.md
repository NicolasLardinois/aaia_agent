# Block 3a: Portfolio-Manager-Ausbau (Richtung + P&L + Exposure) — Design

**Datum:** 2026-06-20
**Status:** Genehmigt (Design)
**Teil von:** Shorts-Programm (`docs/short.md` §12, §16). Erstes Teilstück von Block #3. Fundament für **3b (Track-B-Hedge)** und die **SHORT+-Aktivierung**.

## Kontext & Ziel

Das Depot ist heute **long-only**: Positionen in `data/portfolio.json` sind lose Dicts **ohne Richtung**; der `PortfolioMonitorAgent` liest die Datei **direkt** und rechnet P&L `(current-buy)/buy` (long-only); die `current_position` (none/long/short) kommt im Analyse-Pfad nur über ein **CLI-Flag** (`--position`), nicht aus dem echten Depot.

**Ziel (sauber hexagonal):** Ein **Portfolio-Domänenmodell + Port + JSON-Adapter**. Positionen tragen eine **Pflicht-Richtung** (long/short); der Monitor rechnet **richtungs-bewusst** (Short-P&L invertiert) + **netto/brutto-Exposure** + **Klumpen auf netto** (Pairtrades netten sich aus); die `current_position` wird **aus dem echten Depot** abgeleitet.

## Scope

**Im Block (3a):**
- `Position`-Modell + `PortfolioError`; `PortfolioPort` (ABC); `JsonPortfolioProvider` (liest + validiert).
- `PortfolioMonitorAgent` auf den **Port** umgestellt: richtungs-bewusste P&L, `long/short/net/gross`-Exposure, Klumpen/HHI auf **netto** pro Bucket.
- `current_position` im Analyse-Pfad **aus dem Depot** (`app/main.py`); **CLI-`--position` entfällt**.
- Verdrahtung (`background_runner.py`, `app/main.py`) + Tests.

**Außerhalb (Folge-Schritte):**
- **SHORT+-Aktivierung** (Short-Engine nutzt Einstand/P&L) — eigener kleiner Block danach.
- **Track-B-Hedge** (3b, nutzt `net_exposure`).
- **Schreiben/Editieren** des Depots übers Tool — nicht nötig (JSON manuell gepflegt); Port ist **read-only**.

## Komponenten

### 1. `core/domain/portfolio.py` (neu) — Modell
```python
@dataclass(frozen=True)
class Position:
    ticker: str
    shares: float
    entry_price: float          # aus JSON-Key "buy_price"
    direction: str              # "long" | "short" — PFLICHT
    currency: str = "USD"
    current_price: Optional[float] = None
    sector: str = "Unbekannt"
    asset_class: str = "equity"
    country: str = "Unbekannt"


class PortfolioError(Exception):
    """Ungültige/fehlende Positionsdaten (z. B. fehlende direction)."""
```

### 2. `core/ports/portfolio_port.py` (neu) — Port
```python
class PortfolioPort(ABC):
    @abstractmethod
    def get_positions(self) -> list[Position]: ...
    @abstractmethod
    def position_state_for(self, ticker: str) -> PositionState: ...
```

### 3. `adapters/persistence/json_portfolio.py` (neu) — Adapter
- `JsonPortfolioProvider(PortfolioPort)`, Konstruktor `(path: str = <data/portfolio.json>)`.
- `get_positions()`: liest JSON; je Position-Dict ein `Position`-Objekt. **Validierung:** `direction` muss vorhanden und ∈ {`"long"`,`"short"`} sein — sonst `raise PortfolioError(f"Position {ticker}: direction fehlt/ungültig")`. `entry_price` aus `buy_price`. Fehlt die Datei / leere `positions` → `[]`.
- `position_state_for(ticker)`: aus `get_positions()` den Ticker suchen → `PositionState.LONG`/`SHORT`; nicht gefunden → `PositionState.NONE`.

### 4. `agents/portfolio/portfolio_monitor_agent.py` — auf Port umstellen
- Konstruktor erhält `portfolio_port: PortfolioPort` (injiziert) statt die Datei direkt zu lesen. `run()` nutzt `self.portfolio_port.get_positions()` (in `try/except PortfolioError` → **Alarm** „Portfolio-Daten ungültig: …", kein Crash).
- `_evaluate_positions(positions: list[Position])` arbeitet auf `Position`-Objekten:
  - **richtungs-bewusste P&L** je Position: long `(_cur - entry)/entry`, short `(entry - _cur)/entry`; Verlust-Alert auf dieser P&L.
  - **Wert je Position** (Basiswährung): `shares * current_price * fx` (Betrag).
  - **Exposure-Kennzahlen** im Snapshot: `long_value`, `short_value`, `net_exposure` (long−short), `gross_exposure` (long+short).
  - **Klumpen/HHI auf netto pro Bucket** (sector/asset_class/country): `net_bucket = Σ long − Σ short` im Bucket; `pct = |net_bucket| / gross_exposure`; Alarm wenn `pct > threshold`. → Pairtrade (long+short im selben Sektor) nettet sich zu ~0 → **kein** Klumpen-Alarm.
- **Verdrahtung:** `background_runner.py` → `PortfolioMonitorAgent(memory, portfolio_port=JsonPortfolioProvider())`.

### 5. `app/main.py` — `current_position` aus dem Depot
- `JsonPortfolioProvider` instanziieren; in `run_judgment`: `current_position = port.position_state_for(ticker)` (statt CLI-Flag). Bei `PortfolioError` → `PositionState.NONE` + Warnung.
- Die **`--position`-Argument-Parsing entfernen** (Override gestrichen).

## Datenfluss
`data/portfolio.json` (+`direction`) → `JsonPortfolioProvider` → (a) `PortfolioMonitorAgent` (richtungs-bewusste P&L + netto/brutto + Klumpen-netto); (b) `run_judgment` → `current_position` → Judgment/Short-Engine bekommen die **echte** Position.

## Fehlerbehandlung
- Fehlende/ungültige `direction` → `PortfolioError` (fail-loud). **Monitor fängt** → Alarm (degradiert, kein Crash); **Judgment-Pfad** → `NONE` + Warnung.
- Fehlende Datei / leere Positionen → `[]` (kein Fehler).
- `direction` hat **keinen Default** — Mehrdeutigkeit ist verboten.

## Tests (`tests/`)
- **Modell/Adapter** (`test_json_portfolio.py`): gültige Long/Short-Position → korrektes `Position`/`position_state_for`; **fehlende `direction` → `PortfolioError`**; leere/fehlende Datei → `[]`/`NONE`.
- **Monitor** (`test_portfolio_monitor.py` erweitern/anpassen): Short-Position → **invertierte P&L** (Kursrückgang = Gewinn); `net`/`gross`-Exposure korrekt; **Pairtrade** (long A + short B, gleicher Sektor) → Netto-Sektor ~0 → **kein** Klumpen-Alarm; reines Long-Klumpen weiterhin Alarm. Bestehende Tests auf `Position`-Objekte + injizierten Port umstellen.
- **current_position** (`test_…`): Ticker long/short im Depot → `LONG`/`SHORT`; nicht im Depot → `NONE`.
- **Regression:** Gesamtsuite grün; `background_runner` instanziiert den Monitor korrekt mit Port.

## Akzeptanzkriterien
1. `Position` mit Pflicht-`direction`; `JsonPortfolioProvider` validiert (fehlend → `PortfolioError`).
2. `PortfolioPort` + Adapter; Monitor über den Port injiziert (keine direkte Datei-Lesung mehr im Agenten).
3. Monitor: Short-P&L invertiert; `long/short/net/gross`-Exposure; Klumpen auf **netto** (Pairtrade nettet sich aus).
4. `current_position` kommt aus dem Depot; CLI-`--position` entfernt.
5. Fail-loud bei ungültiger Richtung; Monitor/Judgment degradieren mit Alarm/Warnung statt Crash.
6. Gesamtsuite grün (0 failed).
