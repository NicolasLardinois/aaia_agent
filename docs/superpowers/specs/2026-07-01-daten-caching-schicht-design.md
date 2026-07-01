# Daten-Caching-Schicht („Data Mart hinter den Ports") — Design

> Projektweiter Folge-Task, der in mehreren Specs bereits als „Caching" vorgemerkt wurde
> (z. B. `2026-06-23-eu-geldmenge-ecb-sdw-design.md`, Out-of-Scope). Führt eine gemeinsame
> Caching-/Persistenz-Schicht **hinter** den bestehenden Ports ein, sodass die 40+ Subagenten
> ihre Rohdaten nicht mehr jede für sich live aus der Quelle ziehen, sondern über einen
> datierten Snapshot-Store bedient werden.

**Goal:** Ein Analyselauf zieht jede (Quelle, Serie) **genau einmal**, alle Agenten sehen denselben
eingefrorenen Snapshot (Point-in-Time), Rohdaten werden datiert persistiert (Offline-Resilienz +
Backtest), und bezahlte/limitierte APIs (FMP, Yahoo) werden geschont (Dedup) — **ohne** dass ein
einziger Agent geändert werden muss.

**Architektur:** Event-Driven + Hexagonal. Die Schicht ist ein **Decorator** (im Hexagonal-Sinn „nur
ein weiterer Adapter"), der denselben Port implementiert wie der echte Adapter. Kein neuer
Orchestrierungs-Schritt (Lazy + Memoize, nicht Prefetch).

**Tech-Stack:** Python, pytest. v1 ohne neue externe Libs (JSON-Datei-Store wie `ResultCache` heute).

---

## 1. Befund (Ausgangslage)

- **Hexagonal ist schon da:** Agenten hängen nur an Ports (`core/ports/data_provider.py`:
  `MacroDataProvider`, `EcbDataProvider`, `MarketDataProvider`, …). Der Adapter ist die einzige
  I/O-Stelle. Ein Agent zapft also **heute schon keine API direkt an** — die Indirektion existiert.
- **Was fehlt:** Ein gemeinsamer **Rohdaten**-Layer. Heute kann Agent A einen ECB-Wert von 10:00 und
  Agent B einen von 10:05 sehen; dieselbe Quelle wird pro Lauf mehrfach gezogen; fällt eine Quelle
  aus, gibt es keinen „letzten bekannten Wert".
- **Zwei Vorstufen existieren bereits:**
  - `adapters/cache/result_cache.py` — cached das *Analyse-Ergebnis* (Cockpit / Bottom-up), **nicht**
    die Rohdaten. TTL 1 h, JSON-Datei. Muster für den v1-Store.
  - `core/ports/dated_history.py` (`DatedHistoryPort`, In-Memory/JSON/Supabase) — datierter
    Ein-Wert-pro-Tag-Store, heute für den Regime-Replay-Backtest genutzt. Deckt den **Skalar-Fall**
    des neuen Stores praktisch schon ab.
- **Zwei Daten-Arten** an den Ports:
  - **Skalare/Zeitreihen** (`get_cpi() -> float`, Leitzins-Historie) — passen in `DatedHistoryPort`.
  - **Payloads** (`MarketDataProvider.get_price_history() -> DataFrame`, `get_fundamentals() -> dict`) —
    brauchen einen **Codec** (Serialisierung), passen nicht in eine Ein-Wert-Reihe.

## 2. Scope

**In Scope (v1 / erster PR)**
1. `core/domain/run_context.py` — `RunContext`: Lauf-Identität (`as_of: date`) + In-Memory-Memo.
2. `core/ports/snapshot_store.py` — neuer Port `SnapshotStore` (datierter Key-Value-Store).
3. `adapters/persistence/json_snapshot_store.py` — JSON-Datei-Implementierung (v1-Store).
4. `adapters/data/caching_data_provider.py` — Caching-Decorator mit der Cache-aside-Logik.
   - **ECB-SDW** (`EcbDataProvider`) end-to-end umgehängt → beweist Skalar-/Dedup-/Point-in-Time-Pfad.
   - **Yahoo-Kurshistorie** (`MarketDataProvider.get_price_history`) → beweist den **Payload-Codec**
     (DataFrame-Round-Trip). *(Review-Entscheid 2026-07-01: bleibt in v1.)*
5. `core/utils/dataframe_codec.py` — reine Encode/Decode-Funktionen für pandas-DataFrames/Series.
6. Verdrahtung im Composition-Root: echte Adapter mit dem Decorator umwickeln (nur für die zwei Quellen).
7. Tests (TDD) für RunContext, Store, Decorator, Codec.

**Out of Scope (mit Begründung / Folge-PRs)**
- **Restliche Quellen** (FRED, Eurostat, Finnhub, Fear&Greed, …) — je eine pro Folge-PR (euer
  „1 Quelle/PR"-Stil), Status im Logbuch.
- **Supabase-Store-Adapter** — Folge-PR (v1 nutzt JSON-Datei; Port erlaubt späteren Austausch).
- **Prefetch-Pipeline** — bewusst verworfen (Lazy + Memoize gewählt).
- **Klassisches BI-Warehouse** (Star-Schema/ETL/OLAP) — YAGNI für ein periodisch laufendes Tool.
- **Verhältnis zu `DatedHistoryPort`** — **entschieden (2026-07-01): wiederverwenden.** Der
  Skalar-Zweig des `SnapshotStore` sitzt auf einem `DatedHistoryPort` auf (kein zweiter Zeitreihen-
  Store). Bestehende Backtest-Nutzung von `DatedHistoryPort` bleibt unberührt (nur additive Serien).
- **Retroaktive Historie** — der Store baut Historie erst *ab jetzt* auf. Historische Backtests
  fußen weiter auf `historical_fred.py` o. ä.; die neue Schicht macht künftige Läufe reproduzierbar.

## 3. Komponenten & Datenfluss

### Überblick

```
Agent ──(Port)──► CachingDataProvider ──► echter Adapter (ECB/Yahoo/…) ──► Quelle
                        │
                        ├─ RunContext   (In-Lauf-Memo + as_of-Datum)
                        └─ SnapshotStore (datiert, persistent)
```

Nichts oberhalb des Decorators (Agenten, Chief-Agents, Orchestratoren) ändert sich.

### `RunContext` (core/domain/)

- Felder: `as_of: date` (Live = heute, Backtest = historisches Datum), `memo: dict[tuple, Any]`.
- Zweck: garantiert **1 Fetch pro (Quelle, Serie) pro Lauf** → Point-in-Time **und** Dedup.
- Rein, keine I/O.

### `SnapshotStore` (core/ports/) — neuer Port

```python
class SnapshotStore(ABC):
    @abstractmethod
    def get(self, namespace: str, key: str, as_of: date) -> Optional[Any]:
        """Frischester Wert mit obs_date <= as_of; None wenn nichts vorhanden."""
    @abstractmethod
    def put(self, namespace: str, key: str, obs_date: date, value: Any) -> None:
        """Idempotent pro (namespace, key, obs_date). value = JSON-serialisierbar."""
```

- `namespace` = Quelle/Domäne (z. B. `"ecb"`, `"yahoo.price_history"`), `key` = Serie/Argument
  (z. B. `"cpi"`, `"AAPL:1y"`). `value` = float **oder** codierter Payload (str/dict).
- **v1-Adapter `CompositeSnapshotStore`** — routet nach Wert-Typ (Review-Entscheid 2026-07-01):
  - **float → `DatedHistoryPort`** (Wiederverwendung; Serien-Schlüssel `f"{namespace}:{key}"`).
    Damit fällt der Backtest-Zeitreihen-Fall geschenkt ab und es gibt **keinen** zweiten Skalar-Store.
  - **Payload (str/dict) → JSON-Blob-Datei** (datiert, analog `ResultCache`), da `DatedHistoryPort`
    nur floats hält.
  - `get` fragt beide Zweige (float-Serie zuerst, sonst Blob) und liefert `value_on_or_before(as_of)`.

### `CachingDataProvider` (adapters/data/) — Decorator

Implementiert denselben Port wie der umwickelte Adapter. Zentraler Helfer `_cached(ns, key, fetch)`:

1. **In-Lauf-Memo** (`RunContext.memo`) vorhanden? → zurück (garantiert 1 Fetch/Lauf).
2. Sonst `store.get(ns, key, as_of)` — **frisch genug** (TTL, s. u.)? → memoisieren, zurück.
3. Sonst echten Adapter rufen:
   - **Erfolg & Wert ≠ None** → `store.put(ns, key, as_of, value)` (write-through), memoisieren, zurück.
   - **Exception oder None** → `store.get(ns, key, as_of)` **ohne** Frische-Check (letzter bekannter
     Wert, auch stale) → **Offline-Resilienz**. Ist auch der leer, bleibt es beim Adapter-Verhalten
     (None/Default) — **kein neuer Absturzpfad** (deckt sich mit „eine tote Quelle killt nie den Lauf").

**Backtest fällt geschenkt ab:** identischer Code, nur `as_of` in der Vergangenheit → der Store
liefert `value_on_or_before(as_of)`.

### `dataframe_codec` (core/utils/) — reine Funktionen

- `encode_frame(df) -> str` / `decode_frame(s) -> DataFrame` (analog für `Series`).
- Round-Trip-fest bzgl. **Index (DatetimeIndex!)** und **dtypes** — die heikelste Korrektheits-Stelle,
  daher zuerst per TDD abgesichert. Implementierung via `to_json(orient=..., date_format="iso")` +
  expliziter Index-/dtype-Rekonstruktion.

## 4. Freshness / TTL

- Pro `namespace` konfigurierbar (Makro monatlich ≠ Kurse intraday). **v1: ein konservativer Default**
  (z. B. via `config/settings.py`), Overrides je namespace als Folge-Task. YAGNI.
- Innerhalb eines Laufs ist dank Memo ohnehin alles konsistent; TTL steuert nur die Wiederverwendung
  **zwischen** Läufen (Dedup über Laufgrenzen + wann live nachgezogen wird).

## 5. Fehlerbehandlung

- Decorator wirft **nie** eine neue Exception nach oben: bei Adapter-Fehler → letzter Store-Wert,
  sonst Durchreichen des bestehenden None/Default-Verhaltens.
- Store-Schreibfehler (Disk) dürfen den Lauf nicht killen → geloggt, verschluckt (best effort).
- Deckt sich mit AGENTS.md §2 (Defensive Aggregation, neutraler Default).

## 6. Tests (TDD — zuerst rot)

- **RunContext:** zweiter Zugriff auf dieselbe Serie ruft `fetch` **nicht** erneut (Memo-Hit).
- **SnapshotStore (JSON):** `put`→`get` Round-Trip; `get` mit `as_of` liefert `value_on_or_before`;
  Idempotenz pro (ns, key, obs_date); leerer Store → None.
- **CachingDataProvider:** (a) Memo-Hit, (b) Store-Hit (frisch), (c) Live-Miss + write-through,
  (d) Exception → last-known (auch stale), (e) leerer Store + Exception → Adapter-Default,
  (f) Point-in-Time über zwei Agenten (nur 1 Live-Call).
- **dataframe_codec:** Round-Trip erhält Werte, DatetimeIndex, dtypes; leerer Frame; `Series`.
- **ECB/Yahoo-Integration:** Decorator delegiert korrekt an den echten Adapter (mit Fake-Adapter).

## 7. Rollout (inkrementell)

- **v1 (dieser PR):** Gerüst (RunContext + SnapshotStore-Port + JsonSnapshotStore + Decorator +
  dataframe_codec) + **ECB-SDW** (Skalar-Beweis) + **Yahoo-Kurshistorie** (Codec-Beweis).
- **Folge-PRs (Logbuch):** je eine weitere Quelle umhängen → Supabase-Store-Adapter →
  per-namespace-TTL → optional `DatedHistoryPort`-Konsolidierung.

## 8. Review-Entscheidungen (2026-07-01)

1. **Yahoo bleibt in v1** — der Payload-Codec bekommt so gleich einen echten Nutzer; v1 deckt damit
   beide Daten-Arten (Skalar + Payload) ab.
2. **`DatedHistoryPort` wird wiederverwendet** als Skalar-Backend des `SnapshotStore` (via
   `CompositeSnapshotStore`, s. §3). Keine zwei überlappenden Zeitreihen-Stores; bestehende
   Backtest-Nutzung bleibt unberührt (nur additive Serien).
