# Plan: Agricultural Investment Signal

## Kontext

Der `agricultural_agent` gibt seit Bug #37 ein makroökonomisches Signal aus:
- BEARISH wenn Median der 1J-Preisveränderungen aller 7 Rohstoffe > +20%
- BULLISH wenn Median < -20%

**Idee:** Steigende Agrarpreise (= makro-BEARISH) sind gleichzeitig ein BULLISH-Signal
für Investitionen in Agrar-Rohstoff-ETFs oder -Futures. Diesen Winkel gibt es bisher nicht.

## Ziel

Wenn `agricultural_agent` BEARISH signalisiert → Kontext-Hinweis in der top-down Analyse:
> "Agrarpreise +X% YoY — Rohstoff-ETFs als Inflationsschutz prüfen (z.B. DBA)"

## Betroffene Dateien

- `core/domain/top_down_context.py` — Hinweis-Funktion analog zu `_sovereign_spread_note()`
- `agents/market_cockpit/commodity/agricultural_agent.py` — YoY-Median exportieren (aktuell in `changes` intern)
- `core/domain/models.py` — `AgriculturalSnapshot` um `median_yoy_change: Optional[float]` erweitern

## Tasks

- [ ] `AgriculturalSnapshot` um `median_yoy_change: Optional[float]` erweitern
- [ ] `agricultural_agent.run()`: Median in Snapshot speichern
- [ ] `top_down_context.py`: `_agricultural_note()` für asset_class "commodity" oder "etf"
- [ ] Test: agricultural BEARISH + commodity asset class → Hinweis erscheint

## Relevante ETFs / Ticker

- `DBA` — Invesco DB Agriculture ETF (breit diversifiziert)
- `WEAT` — Teucrium Wheat Fund
- `CORN` — Teucrium Corn Fund
- `SOYB` — Teucrium Soybean Fund
