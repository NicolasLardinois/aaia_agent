# Eurozone-Makro Slice 2 (EU-Geldmenge, ECB SDW) — Design

> Slice 2 der Eurozone-Makro-Anbindung (nach Slice 1 / Eurostat, PR #38). Bindet M2/M3 via
> ECB SDW an **und** schaltet das EU-Geldmengensignal scharf (kleiner Agenten-Tweak: nominales BIP).
> Anders als die bisherigen Slices berührt diese Slice bewusst **Agenten-Logik** — daher TDD auf den Agenten.

**Goal:** Das EU-Geldmengensignal (`money_supply_agent`) liefert reale Werte statt NEUTRAL, indem
(1) `EcbSdwProvider` echte M2/M3-Jahreswachstumsraten liefert und (2) der Agent das nominale BIP
(reales BIP + CPI) berechnet, das er für die Überschuss-Liquidität braucht.

**Architektur:** Event-Driven + Hexagonal. **Keine Verdrahtungsänderung** nötig — seit Slice 1 ist
`ecb = EurostatEcbProvider(EcbSdwProvider())` verkabelt, und der Decorator delegiert `get_m2_growth`/
`get_m3_growth` bereits an die Basis. Sobald die Basis echte Werte liefert, fließen sie durch.

**Tech-Stack:** Python, `requests`, pytest.

---

## 1. Befund (Ausgangslage)

- `EcbSdwProvider.get_m2_growth`/`get_m3_growth` sind Stubs → `None` (`ecb_sdw.py:94,102`).
- `money_supply_agent` konsumiert `ecb.get_m2_growth`/`get_m3_growth`, aber das EU-Signal bleibt selbst
  mit M-Daten NEUTRAL, weil `eu_nom_gdp = None` (`money_supply_agent.py:68`, TODO). Ohne nominales BIP
  ist die Überschuss-Liquidität nicht berechenbar.
- Die USA macht es bereits richtig (`money_supply_agent.py:56-60`): `nom_gdp = reales BIP + CPI` (lineare
  Fisher-Proxy), `excess = M2-Wachstum − nom_gdp` via `excess_over_nominal_gdp` (`core/utils/real_nominal.py`).
- `ecb.get_gdp_growth` und `ecb.get_cpi` sind seit Slice 1 (Eurostat) **echt verfügbar** — die Bausteine
  für das EU-nominale-BIP sind also schon da.
- **Verifiziert (2026-06-23) gegen die ECB-SDW-API** (gleicher Host wie der bestehende `_fetch_yield`):
  - M3-Jahreswachstum: `BSI/M.U2.Y.V.M30.X.I.U2.2300.Z01.A` → 2,74 % („Monetary aggregate M3, Annual growth rate", %).
  - M2-Jahreswachstum: `BSI/M.U2.Y.V.M20.X.I.U2.2300.Z01.A` → 2,87 %. (Nur `M30` vs `M20` unterscheidet sich.)

## 2. Scope

**In Scope**
1. `adapters/data/ecb_sdw.py`: `get_m2_growth`/`get_m3_growth` echt (ECB SDW BSI), plus reine
   `_parse_sdmx_last_observation`-Funktion. Die bestehenden `_fetch_yield`/`_fetch_country_yield`
   nutzen denselben Helfer (DRY; identisches SDMX-Parsing war 3× dupliziert) — **verhaltens-erhaltend**.
2. `agents/market_cockpit/macro/money_supply_agent.py`: EU-Pfad rechnet `eu_nom_gdp = ecb_gdp + ecb_cpi`
   (analog USA) → EU-Geldmengensignal schaltet scharf.
3. Tests (TDD) für Adapter **und** Agent.

**Out of Scope (mit Begründung)**
- **CH-Geldmenge / SNB-nominal-BIP** — `ch_nom_gdp` bleibt `None` (separate spätere CH-Makro-Slice).
- **PMI** (proprietär, deferred), **Caching** (projektweiter Folge-Task).
- **Keine Verdrahtungsänderung** (`app/main.py`/`app/server.py` unverändert — Delegation existiert).
- Bestehende Signal-Schwellen (`_signal`) **unverändert** — nur die Input-Berechnung (`eu_nom_gdp`) wird ergänzt.

## 3. Komponenten & Datenfluss

```
money_supply_agent.run()
  ├─ ecb.get_m2_growth / get_m3_growth ─┐ (Decorator delegiert an EcbSdwProvider)
  ├─ ecb.get_gdp_growth / get_cpi ──────┤ (Decorator → Eurostat, seit Slice 1 echt)
  ▼                                      ▼
  eu_m = m3 ?? m2;  eu_nom_gdp = gdp + cpi
  eu_excess = excess_over_nominal_gdp(eu_m, eu_nom_gdp)  → _signal(eu_excess, None)
```

**Adapter (`EcbSdwProvider`):**
- `_parse_sdmx_last_observation(data: dict) -> float | None` — rein: letzter Beobachtungswert aus
  ECB-SDMX-JSON (`dataSets[0].series[…].observations`, jüngste); `None` bei fehlender Struktur/leer/nicht-numerisch.
- `_fetch_bsi_growth(item: str) -> float | None` — baut die BSI-URL (`M30`/`M20`), `requests.get`,
  `_parse_sdmx_last_observation`; Sanity-Cap `-50…50 %`, Rundung 1 Stelle; Fehler/implausibel →
  `logging.warning` → `None` (Beobachtbarkeit wie CNN/Eurostat).
- `get_m3_growth` → `_fetch_bsi_growth("M30")`; `get_m2_growth` → `_fetch_bsi_growth("M20")`.
- `_fetch_yield`/`_fetch_country_yield` rufen künftig `_parse_sdmx_last_observation` (verhaltens-erhaltend).

**Agent (`money_supply_agent`):**
- `asyncio.gather` zusätzlich um `ecb.get_gdp_growth` + `ecb.get_cpi` erweitern.
- `eu_nom_gdp = (ecb_gdp + ecb_cpi) if (ecb_gdp is not None and ecb_cpi is not None) else None`.
- `eu_excess = excess_over_nominal_gdp(eu_m, eu_nom_gdp) if (eu_m is not None and eu_nom_gdp is not None) else None`.
- CH-Block unverändert.

## 4. Finanzielle Korrektheit (AGENTS.md §3)

- **Einheit:** M2/M3 kommen als Jahreswachstumsrate **in %** (z. B. 2,7) — passt direkt zur Überschuss-
  Logik in Prozentpunkten. Kein Index-Rechnen.
- **Nominaler-BIP-Proxy:** `reales BIP + CPI` ist die lineare Fisher-Näherung; CPI dient als Deflator-Proxy
  (GDP-Deflator ≠ CPI, aber etablierte Vereinfachung — **identisch** zur bestehenden USA-Logik, daher
  projektkonsistent). Im Kommentar benannt.
- **M3 bevorzugt:** EZB-Headline-Geldmenge ist M3 → `eu_m = m3 ?? m2`.
- **Plausibilität:** Beispiel M3 2,7 − nom. BIP (0,3+2,0=2,3) = 0,4pp → gesunder Bereich → BULLISH.

## 5. Fehler & Tests (TDD, zuerst rot)

`tests/adapters/test_ecb_sdw_money.py` (oder bestehende ECB-Testdatei):
- `_parse_sdmx_last_observation`: gültige SDMX-Struktur → Wert; fehlende Keys/leer/nicht-numerisch → `None`.
- `get_m3_growth`/`get_m2_growth` mit gemocktem `requests.get` (eingefangene BSI-Antwort) → Wert (gerundet);
  Sanity-Cap (implausibel → `None`); Netzfehler → `None`. Test pinnt `M30`/`M20` in der URL.
- Regression: bestehende Yield-Spread-/Sovereign-Tests bleiben grün (Helfer-Refactor verhaltens-erhaltend).

`tests/agents/market_cockpit/macro/test_money_supply_agent.py` (Agent):
- EU mit echten Inputs (M3=2,7, BIP=0,3, CPI=2,0) → `eu_excess` ≈ 0,4 → Signal **BULLISH**, `status` AVAILABLE.
- EU ohne BIP **oder** ohne CPI → `eu_nom_gdp=None` → `eu_excess=None` → Signal **NEUTRAL** (kein Crash).
- M3 fehlt, M2 vorhanden → `eu_m` fällt auf M2 zurück.

## 6. Logbuch / Doku

- `docs/open_todos.md`: „EU-Geldmenge (Slice 2)"-Folge-Task abhaken mit Lösungsvermerk.
- README: keine Änderung (reine Datenanbindung + minimaler, projektkonsistenter Agenten-Tweak).

## 7. Risiken / Annahmen

- ECB-SDW BSI-Series-Keys gegen die echte API verifiziert; Antwortstruktur SDMX-JSON (wie bestehende Yield-Fetches).
- Kein API-Key (öffentlich). Bei Strukturänderung → `UNAVAILABLE` (+ WARNING), kein Crash.
- Mehr Live-Calls pro Lauf (gdp/cpi nun auch im money_supply_agent) — vom bestehenden Caching-Folge-Task abgedeckt.
