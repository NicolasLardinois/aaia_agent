# Spec — Echter `fetchDeepDive`-Anschluss (Deep-Dive pro Ticker)

> Status: Entwurf (2026-06-26). Laufender Status/Reihenfolge steht im Logbuch `docs/open_todos.md`, nicht hier.
> Ziel der Initiative „Echte Daten statt Stubs": die Demo-Tausch-Naht im Deep-Dive durch einen echten
> Backend-Endpunkt ersetzen, der den `DeepDiveView`-Vertrag erfüllt.

## 1. Kontext & Ist-Zustand

- **Frontend (Tausch-Naht):** `frontend/src/data/deepdive.ts` → `loadDeepDive(ticker)` liefert heute `demoDeepDive(ticker)`.
  Die echte Zeile (`return fetchDeepDive(ticker, _deps)`) ist auskommentiert. Beim Umstieg wird **genau diese eine Zeile** getauscht (setzt `isDemo:false`); die UI bleibt unverändert, weil der Vertrag identisch ist.
- **Vertrag:** `frontend/src/contract/deepdive.ts` → `DeepDiveView` (Ticker/Name/underlying/wrapper/Preis/Markt/`found`,
  `long`/`short`-Linse mit XAI, `anomaly`, kontextabhängige Blöcke `equity?`/`bond?`/`index?`/`commodity?`/`futures?`,
  `cockpitWind?`, `backtestContext?`). `signal=null` ⇒ UNAVAILABLE (nie 0/neutral).
- **Backend liefert die Substanz bereits:**
  - `BottomUpOrchestrator.run(ticker, …)` → `BottomUpResult` (führt je underlying den passenden Chief aus:
    equity/bond/index/commodity/precious; trägt `fundamentals/quality/short_interest/insider/earnings_trend/moat/valuation_range/bond/index/commodity_deep/momentum/fund_info`).
  - `JudgmentOrchestrator.run(cockpit, bottom_up, …)` → `DeepDiveResult` (Urteil: `recommendation`, `judgment`,
    `alignment`, `dominant_signal`, `confidence`, `xai_explanation`, `top_down_anomaly`/`bottom_up_anomaly`,
    `short_action`/`short_assessment`/`short_thesis`/`short_xai`, `conflict*`).
- **Es gibt heute KEINEN Deep-Dive-Endpunkt** (nur das Cockpit unter `/api/cockpit`). Der Cockpit-Lauf ist ein
  **Singleton-Hintergrundlauf** (`RunManager`): `POST /api/cockpit/run` startet, Fortschritt via WS, `latest` wird
  gecacht, `GET /api/cockpit` serialisiert via `cockpit_serializer.cockpit_to_dict`.

## 2. Ziel

Ein echter, vertrags­treuer Deep-Dive pro Ticker:

```
GET  /api/deepdive/{ticker}        -> DeepDiveView (oder 204, falls noch nicht gelaufen)
POST /api/deepdive/{ticker}/run    -> 202 (startet Hintergrund-Analyse), 409 falls für den Ticker schon läuft
WS   /ws/deepdive?ticker=…&token=… -> Fortschritt + terminales DeepDiveResultReady
```

Plus `deepdive_serializer.deepdive_to_dict(result) -> dict` (rein, spiegelt `cockpit_serializer`),
plus `frontend/src/data/api/deepdive.ts` (`fetchDeepDive`) + Tausch-Naht-Zeile aktivieren.

## 3. Schlüssel-Entscheidung — Lauf-Modell & **Kosten** (gehört dem User)

Anders als das Cockpit (1 Lauf/Tag, alles auf einmal) wird ein Deep-Dive **on demand pro Ticker** ausgelöst.
Jeder echte Lauf zieht externe Daten **und** eine **Claude-XAI-Erklärung** (`xai_explanation`/`short_xai`) → echte
API-Kosten + Latenz pro Aufruf. Deshalb sind hier zwei Hebel zu entscheiden, bevor implementiert wird:

> **ENTSCHEIDUNG (User, 2026-06-26): A + X1.** Hintergrund-Lauf + Cache + WebSocket (wie Cockpit) **und**
> echte Claude-XAI sofort. Begründung: höchster fachlicher Wert; Kosten pro Lauf werden über Caching/TTL pro
> Ticker gemildert. Damit hängt PR-2 (Endpunkt) an einem pro-Ticker-`DeepDiveRunManager` + WS, und der Lauf
> erzeugt die XAI-Erklärung live (Claude-Adapter, schon im Judgment vorhanden).

1. **Lauf-Architektur — gewählt: (A)**
   - **(A) Hintergrund + Cache + WS** (wie Cockpit): konsistent zum bestehenden Muster, nicht-blockierend,
     Fortschritt sichtbar; pro Ticker ein eigener Lauf-Lock + eigener `latest`-Cache (Dict statt Singleton).
   - ~~(B) Synchroner Request mit Timeout~~ — verworfen (blockiert auf Render-Free-Tier).

2. **XAI-Kostenschalter — gewählt: (X1)**
   - **(X1) Voll-Echt sofort:** jeder Deep-Dive ruft Claude für die XAI-Erklärung (höchster fachlicher Wert, Kosten/Lauf).
   - ~~(X2) Daten echt, XAI später~~ — verworfen; der fachliche Wert der live generierten Erklärung überwiegt.
   - **Kostendämpfung (Pflicht in PR-2):** Caching/TTL pro Ticker, damit wiederholte Aufrufe desselben Tickers
     keinen neuen Claude-Lauf auslösen.

## 4. Feld-Mapping (Quelle → `DeepDiveView`)

> Pures Mapping im Serializer (snake→camel), kein I/O. „n.v." = im Backend (noch) nicht vorhanden ⇒ UNAVAILABLE.

| `DeepDiveView` | Quelle (`DeepDiveResult` / `BottomUpResult`) | Status |
|---|---|---|
| `ticker`,`underlying`,`wrapper`,`market` | `DeepDiveResult.{ticker,underlying,wrapper,market}` | ✅ |
| `found` | true, falls Lauf ein Ergebnis hat | ✅ |
| `name`,`price`,`currency` | aus `bottom_up`-Preis-Snapshots (je underlying) | teils |
| `long` (verdict/confidence/rationale/xai) | `recommendation.action`+`confidence`+`reasoning`, `xai_explanation`/`dominant_signal` | ✅ (xai s. §3 X2) |
| `short` | `short_assessment`/`short_action`/`short_thesis`/`short_xai` | ✅ |
| `anomaly` | `bottom_up_anomaly` (+ ggf. `top_down_anomaly`) → severity/outliers/conflicts | ✅ |
| `equity` | `bottom_up.{valuation_range,fundamentals,quality,short_interest,insider,earnings_trend,moat}` | ✅ (B1-Katalog) |
| `bond` | `bottom_up.bond` (duration/rating/spread) | ✅ |
| `index` | `bottom_up.index` (pe/breadth/momentum/composition) | teils (breadth n.v.) |
| `commodity` | `bottom_up.commodity_deep`/`precious_metals` (supply-demand/seasonality/cot/cross-metal) | ✅ |
| `futures` | Futures-Roll-Kennzahlen (Hülle=future) | **n.v.** (Backend-Lücke; Folge) |
| `cockpitWind` | `top_down_context`/Cockpit-Domänensignal | teils |
| `backtestContext` | Backtest-Speicher pro Ticker | **n.v.** (Folge) |

## 5. Schnitte (je eigener PR, TDD)

1. **PR-1 — `deepdive_serializer` (rein, kostenlos).** `deepdive_to_dict(DeepDiveResult) -> dict` per Fixture-`DeepDiveResult`
   getestet; Core + Long/Short + Anomaly + **equity**-Block zuerst (häufigster Fall), übrige Blöcke UNAVAILABLE-fest.
   Spiegelt `cockpit_serializer`. **Keine** echten Läufe/Kosten → ideal als Einstieg.
2. **PR-2 — Endpunkt + Lauf-Manager.** `DeepDiveRunManager` (pro-Ticker-Lock + Cache), Route `routes_deepdive.py`,
   Wiederverwendung des **letzten Cockpit-Laufs** als Top-Down-Kontext (`run_manager.latest`); XAI gem. §3-Entscheid.
3. **PR-3 — Frontend-Anschluss.** `data/api/deepdive.ts` (`fetchDeepDive`, mappt Antwort → `DeepDiveView`),
   Tausch-Naht in `data/deepdive.ts` aktivieren; Lade-/`läuft`-Zustand analog Cockpit.
4. **Folge** — Futures-Roll-Kennzahlen + `backtestContext` echt (Backend-Lücken), `index.breadth`, Claude-XAI (falls X2).

## 6. Querschnitt-Regeln

- **UNAVAILABLE ≠ 0/neutral** durchgängig (`signal:null`, Zahl `null`), Quell-Zähler in `SourceHealthMeta`.
- **Region/Asset-Klasse korrekt:** nur der zum `underlying` passende Block ist gesetzt (Edelmetall ≠ Aktie ≠ Bond).
- **Secrets/Fehler:** Fehlerdetails nur ins Server-Log, nie an den Client (Repo öffentlich), wie `RunManager`.
- **TDD verpflichtend**, Tests spiegeln `tests/adapters/api/…` (Serializer) bzw. `frontend/src/data/…`.

## 7. Offene Entscheidungen (vor PR-2)

- ~~§3.1 Lauf-Architektur + §3.2 XAI-Kostenschalter~~ → **entschieden: A + X1** (2026-06-26).
- Ticker-Auflösung underlying/wrapper (woher? bestehender Resolver im Cockpit/Universe wiederverwenden).
- Caching-TTL pro Ticker (Render-Free-Tier-Cold-Start beachten) — jetzt **Pflicht** wegen X1-Kosten.
