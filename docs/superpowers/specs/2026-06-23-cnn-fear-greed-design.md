# CNN Fear & Greed — Daten-Adapter & Verdrahtung — Design

> Erste Slice der Initiative „Stubs → echte Datenquellen". Bewusst die kleinste Quelle
> zuerst, um das Muster **echter Adapter + Port-Injektion + TDD + Verifikation** einmal
> sauber end-to-end zu etablieren. Folge-Slices (EU-/CH-Makro, Bond-Daten, COT …) sind
> eigene PRs — siehe Logbuch `docs/open_todos.md`.

**Goal:** Den CNN-Fear-&-Greed-Index als echte Live-Datenquelle anbinden, sodass die
Sentiment-Dimension im Market-Cockpit (CLI-Dashboard *und* API/Frontend) reale Werte
statt `UNAVAILABLE` liefert.

**Architektur:** Event-Driven + Hexagonal. Der Agent hängt ausschließlich am Port
`SentimentDataProvider`; der konkrete Adapter wird über die Composition Roots
(`app/main.py`, `app/server.py`) injiziert. I/O lebt nur im Adapter.

**Tech-Stack:** Python, `requests`, pytest.

---

## 1. Befund (Ausgangslage)

- `agents/market_cockpit/sentiment/fear_greed_agent.py` ist **fachlich vollständig**:
  nimmt optional einen `SentimentDataProvider`, ruft `get_fear_greed()` in einem Thread
  ab, behandelt `None` → `SignalStatus.UNAVAILABLE`. Schwellen entsprechen den offiziellen
  CNN-Bändern (0–25 Extreme Fear … 75–100 Extreme Greed), contrarian nur in den Extremen
  (≤25 → BULLISH, ≥75 → BEARISH; Review-Punkt D3, erledigt). **Bleibt unverändert.**
- **Zwei Lücken:** (1) kein echter Adapter; (2) `SentimentChiefAgent` konstruiert
  `FearGreedAgent(bus)` **ohne** Provider → selbst ein fertiger Adapter käme nie an.
- In Produktion (`app/main.py` `run_dashboard`, `app/server.py`) wird der Sentiment-Provider
  heute nirgends injiziert → Fear & Greed ist dauerhaft `UNAVAILABLE`.

## 2. Scope

**In Scope**
1. Neuer Adapter `adapters/data/cnn_fear_greed.py`.
2. Optionaler `sentiment`-Provider durch `SentimentChiefAgent` und `TopDownOrchestrator`
   durchgereicht; injiziert in `app/main.py` + `app/server.py`.
3. Entfernen des redundant gewordenen `adapters/data/sentiment_stub.py`
   (`SentimentStubProvider`) inkl. zugehörigem Test.
4. Tests (TDD).

**Out of Scope (mit Begründung)**
- Signal-/Label-Logik des Agenten — bereits korrekt und getestet; Anfassen ohne Anlass
  riskiert stillen Finanzfehler (AGENTS.md §3).
- Alle anderen Stubs (EU-/CH-Makro, Bond, COT, Index-Breadth, Redis) — je eigene PR.
- Der Replay (`app/replay_regime.py`) bleibt bewusst ohne Live-Sentiment (historisch).

## 3. Komponenten & Datenfluss

```
app/main.py | app/server.py
        │ injiziert CnnFearGreedProvider()
        ▼
TopDownOrchestrator(..., sentiment=…)
        │ reicht durch
        ▼
SentimentChiefAgent(market, bus, sentiment=…)
        │ baut FearGreedAgent(bus, provider=sentiment)
        ▼
FearGreedAgent.run()  ──get_fear_greed()──▶  CnnFearGreedProvider  ──HTTP──▶  CNN
```

Default in beiden Konstruktoren: `sentiment=None` → alle bestehenden Tests und der Replay
bleiben offline-sicher und verhalten sich exakt wie bisher (UNAVAILABLE).

## 4. Adapter-Design `CnnFearGreedProvider`

- Quelle: `https://production.dataviz.cnn.io/index/fearandgreed/graphdata/`.
- **I/O und Parsing getrennt:** reine Funktion `_parse(data: dict) -> float | None`
  extrahiert den aktuellen Wert; `get_fear_greed()` macht nur den HTTP-Call und ruft `_parse`.
- **Reale Fallstricke (bewusst behandelt):**
  - CNN antwortet ohne Browser-`User-Agent` mit HTTP 418 → Header wird gesetzt.
  - Aktueller Wert liegt unter `data["fear_and_greed"]["score"]` (das alte TODO im Stub
    vereinfachte fälschlich auf flaches `{"score": …}`).
- **Datenkorrektheit (AGENTS.md §3):** Einheit ist **0–100** (passt exakt zu den Agenten-
  Schwellen — keine Dezimal-/Prozent-Verwechslung). Sanity-Cap: Wert außerhalb `[0, 100]`
  oder nicht-numerisch → `None`. Rundung auf 1 Nachkommastelle.
- **Fehlerverhalten:** jede Exception (Netz, HTTP-Status, JSON, Parsing) → `None` →
  Agent liefert sauber `UNAVAILABLE`. Eine ausgefallene Quelle darf die Analyse nie crashen.

## 5. Tests (TDD, zuerst rot)

`tests/adapters/data/test_cnn_fear_greed.py`:
- `_parse` (rein, kein Netz): gültiger Score; verschachtelte Struktur korrekt; fehlender
  Key → `None`; nicht-numerisch → `None`; außerhalb 0–100 (z. B. 150, -5) → `None`;
  Grenzen 0 und 100 → gültig.
- Adapter mit gemocktem `requests.get` (Fake-Response): liefert den Score; wirft
  `requests.get` → `None` (defensiver Pfad).

`tests/test_integration_wiring.py` (Verdrahtung):
- `test_sentiment_stub_provider_returns_none` **entfernen** (Stub verschwindet).
- Neu: `SentimentChiefAgent(market, bus, sentiment=Fake(score=10))` → `fear_greed.value == 10`,
  `signal == BULLISH` (Extreme Fear), `status == AVAILABLE`.
- Bestehender Test „ohne Provider → value is None" bleibt grün (Default `None`).

## 6. Risiken / Annahmen

- CNN-Endpoint ist inoffiziell; Antwortstruktur kann sich ändern → `_parse` ist defensiv,
  Fehler degradiert zu `UNAVAILABLE` (kein Crash). Bei dauerhaftem Bruch: eigener Folge-Task.
- Kein API-Key nötig (öffentlicher Endpoint) → keine Secret-/`.env`-Änderung.

## 7. Logbuch / Doku

- `docs/open_todos.md`: Fear-&-Greed-/Sentiment-Stub-Eintrag abhaken mit Lösungsvermerk;
  Stub-Entfernung notieren.
- README: keine Änderung (kein konzeptionelles/inhaltliches Delta — reine Datenanbindung).
