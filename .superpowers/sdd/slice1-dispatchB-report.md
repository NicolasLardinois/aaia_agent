# Slice 1 Dispatch B — Report

Datum: 2026-06-23
Branch: feat/frontend-slice1-cockpit-drilldowns

---

## Zusammenfassung

Alle 7 Tasks B1–B7 vollständig implementiert. TDD rot→grün je Task. US3/US4/US8/US9 sichtbar abgedeckt.

---

## Task B1 — DrilldownShell

**Dateien:**
- `frontend/src/pages/cockpit/DrilldownShell.tsx` (neu)
- `frontend/src/pages/cockpit/DrilldownShell.test.tsx` (neu, 7 Tests)

**Commit:** `500db0f`

**TDD-Evidenz:**
- Rot: Datei fehlte (ImportError)
- Grün: 7/7 Tests bestanden

**Abgedeckte Assertions:**
- Titel + Zurück-Link `/cockpit` vorhanden
- DemoBadge bei `isDemo=true` sichtbar, bei `false` nicht
- SourceHealth zeigt `2/3 Quellen aktiv + ⚠`
- Loading → „Lädt …", keine children
- Error → Fehlertext, keine children
- Normal → children gerendert

---

## Task B2 — Makro-Drilldown (US3)

**Dateien:**
- `frontend/src/pages/cockpit/MacroDrilldown.tsx` (neu)
- `frontend/src/pages/cockpit/MacroDrilldown.test.tsx` (neu, 6 Tests)

**Commit:** `ed1bfc2`

**TDD-Evidenz:** 6/6 Tests grün

**Abgedeckte Assertions:**
- USA, DE, CH gezeigt — KEIN „EU"-Eintrag
- USA 3.2% → greifende Schwelle „3–4 % (erhöht)" + BEARISH-Badge
- DE 2.4% → „1–3 % (Zielzone)" + BULLISH
- CH 1.1% → CH-spezifisch „0.5–2 % (Zielzone)"
- Demo-Badge + dataDate je Region

---

## Task B3 — Rohstoffe-Drilldown

**Dateien:**
- `frontend/src/pages/cockpit/CommoditiesDrilldown.tsx` (neu)
- `frontend/src/pages/cockpit/CommoditiesDrilldown.test.tsx` (neu, 5 Tests)

**Commit:** `505b217`

**TDD-Evidenz:** 5/5 Tests grün

**Abgedeckte Assertions:**
- „Rohoel (WTI)" mit BULLISH
- „Kupfer" mit BEARISH
- „Erdgas" mit NEUTRAL
- Demo-Badge + Note-Texte sichtbar

---

## Task B4 — Sentiment-Drilldown

**Dateien:**
- `frontend/src/pages/cockpit/SentimentDrilldown.tsx` (neu)
- `frontend/src/pages/cockpit/SentimentDrilldown.test.tsx` (neu, 4 Tests)

**Commit:** `f634eec`

**TDD-Evidenz:** 4/4 Tests grün

**Abgedeckte Assertions:**
- VIX (18.2) + NEUTRAL
- Fear & Greed (62) + BEARISH
- Demo-Badge + Note-Texte

---

## Task B5 — Zinskurve-Drilldown (US4)

**Dateien:**
- `frontend/src/pages/cockpit/YieldCurveDrilldown.tsx` (neu, LineCurve + 3 Spreads + Inversions-Status)
- `frontend/src/pages/cockpit/YieldCurveDrilldown.test.tsx` (neu, 4 Tests)

**Commit:** `bfdf50a`

**TDD-Evidenz:** 4/4 Tests grün

**Abgedeckte Assertions:**
- 3 Spread-Paare (10J-2J, 10J-3M, 30J-10J) mit Werten
- Status „nicht invertiert" bei allen positiven Spreads
- Status „invertiert → Rezessions-Frühsignal" bei negativem Spread
- Demo-Badge sichtbar

**Abweichung:** `getByText(/invertiert/i)` findet mehrere Elemente (Badge + Status-Block) → `getAllByText` verwendet.

---

## Task B6 — Sektoren-Drilldown (US8, UNAVAILABLE-Pfad)

**Dateien:**
- `frontend/src/pages/cockpit/SectorsDrilldown.tsx` (neu)
- `frontend/src/pages/cockpit/SectorsDrilldown.test.tsx` (neu, 6 Tests)

**Commit:** `09f0af1`

**TDD-Evidenz:** 6/6 Tests grün

**Abgedeckte Assertions:**
- Regime „AUFSCHWUNG" sichtbar
- Technologie: favored + BULLISH-Badge
- Versorger: avoid + BEARISH-Badge
- Energie: `signal=null` → UnavailableField „nicht verfügbar" (NICHT neutral/0)
- SourceHealth: „2/3 Quellen aktiv" + ⚠

---

## Task B7 — Klickbare Kacheln + Routing

**Dateien:**
- `frontend/src/components/DomainTile.tsx` (modifiziert: `<div>` → `<Link>`)
- `frontend/src/components/DomainTile.test.tsx` (neu, 5 Tests)
- `frontend/src/pages/CockpitPage.tsx` (modifiziert: Makro-Link + Buffett/Big-Mac-Schnellzugriff)
- `frontend/src/pages/CockpitPage.test.tsx` (modifiziert: MemoryRouter ergänzt)
- `frontend/src/routes.tsx` (modifiziert: 5 neue Drilldown-Routen + 2 Platzhalter)
- `frontend/src/routes.test.tsx` (modifiziert: 5 neue Routing-Tests)

**Commit:** `cc1e850`

**TDD-Evidenz:** DomainTile 5/5, routes 7/7 Tests grün. CockpitPage 4/4 weiterhin grün.

**Abgedeckte Assertions:**
- Kachel Rohstoffe = Link mit href `/cockpit/commodities`
- yield_curve → Slug `yield-curve` (underscore→hyphen)
- UNAVAILABLE-Kachel ist trotzdem klickbar
- Navigation zu /cockpit/macro, /cockpit/yield-curve, /cockpit/commodities, /cockpit/sentiment, /cockpit/sectors rendert jeweiligen Drilldown
- Zurück-Link je Drilldown vorhanden

**Konsequenz:** CockpitPage.test.tsx um `MemoryRouter` erweitert (DomainTile als Link braucht Router-Kontext). Bestehende 4 Tests weiterhin grün.

---

## Zusätzlicher Fix: tslib (pre-existing Build-Fehler)

`tslib` fehlte als Laufzeit-Abhängigkeit für `echarts-for-react` (ESM) — der Build schlug schon vor Dispatch B fehl. Fix: `npm install tslib`. **Commit:** `c0e83c9`

---

## US-Abdeckung (Dispatch B)

| US | Task | Abgedeckt |
|---|---|---|
| US3 | B2 MacroDrilldown | ✓ USA/DE/CH-Inflation + greifende Schwellen |
| US4 | B5 YieldCurveDrilldown | ✓ LineCurve + 3 Spreads + Inversions-Flag |
| US8 | B6 SectorsDrilldown | ✓ Rotation je Regime + UNAVAILABLE-Pfad |
| US9 | B1 DrilldownShell + B6 | ✓ SourceHealth je Drilldown, 2/3-Warnung sichtbar |

---

## Abschluss-Verifikation

### npm test

```
Test Files  43 passed (43)
     Tests  186 passed (186)
```

Alle 43 Test-Dateien grün (inkl. Slice-0-Bestandstests).

### npm run build

```
✓ built in 4.52s
```

Erfolgreich nach `tslib`-Fix. Chunk-Size-Warnung (ECharts ~1 MB) ist eine Warnung, kein Fehler.

---

## Geänderte Dateien (Dispatch B)

- `frontend/src/pages/cockpit/DrilldownShell.tsx` (neu)
- `frontend/src/pages/cockpit/DrilldownShell.test.tsx` (neu)
- `frontend/src/pages/cockpit/MacroDrilldown.tsx` (neu)
- `frontend/src/pages/cockpit/MacroDrilldown.test.tsx` (neu)
- `frontend/src/pages/cockpit/CommoditiesDrilldown.tsx` (neu)
- `frontend/src/pages/cockpit/CommoditiesDrilldown.test.tsx` (neu)
- `frontend/src/pages/cockpit/SentimentDrilldown.tsx` (neu)
- `frontend/src/pages/cockpit/SentimentDrilldown.test.tsx` (neu)
- `frontend/src/pages/cockpit/YieldCurveDrilldown.tsx` (neu)
- `frontend/src/pages/cockpit/YieldCurveDrilldown.test.tsx` (neu)
- `frontend/src/pages/cockpit/SectorsDrilldown.tsx` (neu)
- `frontend/src/pages/cockpit/SectorsDrilldown.test.tsx` (neu)
- `frontend/src/components/DomainTile.tsx` (modifiziert)
- `frontend/src/components/DomainTile.test.tsx` (neu)
- `frontend/src/pages/CockpitPage.tsx` (modifiziert)
- `frontend/src/pages/CockpitPage.test.tsx` (modifiziert)
- `frontend/src/routes.tsx` (modifiziert)
- `frontend/src/routes.test.tsx` (modifiziert)
- `frontend/package.json` + `frontend/package-lock.json` (tslib-Fix)
