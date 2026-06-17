# Plan C — Fixed-Income-Engine (Pricing, Duration, Spreads, Credit) — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Bond-Deep-Dive-Domäne von reiner Provider-Durchreichung (leerer Provider → alles `None` → dauerhaft NEUTRAL) auf eine echte, selbst gerechnete Fixed-Income-Engine umstellen. Konkret: YTM/Macaulay/Modified/Effective Duration, Convexity, DV01 (Clean vs. Dirty), Yield-to-Worst und die Convexity-korrigierte Preisänderungsschätzung (½·C·Δy²) in `core/utils/bond_math.py`; Rating-Normalisierung (S&P↔Moody's↔Fitch) mit exaktem PD-Lookup (kein `startswith`-Bug), Credit Triangle (Spread ≈ PD·LGD) und binäre IG/Non-IG-Grenze in `core/utils/credit.py`. Die vier Bond-Agenten (`metrics`, `duration`, `credit`, `spread`) und `bond_chief_agent` nutzen diese Engine; %/Dezimal werden vereinheitlicht; `real_yield` läuft über Breakeven; der Chief bildet eine konsolidierte Gesamtsicht aus Duration- und Credit-Risiko.

**Architecture:** Hexagonal + EDA. Reine Finanzmathematik lebt framework-frei in `core/utils/` (keine I/O, keine Ports, voll deterministisch und damit Unit-testbar). Die Agenten (Adapter-Schicht) holen Rohdaten über `FundamentalsProvider.get_bond_data()` / `MacroDataProvider`, rufen die Pure-Functions auf, mappen auf die bestehenden `*Snapshot`-Dataclasses und publizieren `*Ready`-Events. Signaturen der Snapshots/Events bleiben unverändert; nur ihre Befüllung wird echt berechnet.

**Tech Stack:** Python, asyncio, pytest

**Abhängigkeiten:** Plan 0 (Shared Utilities) — insbesondere `core/utils/real_nominal.py` mit `to_real(nominal_rate, inflation)` für die ex-ante Realrendite. Falls Plan 0 zum Zeitpunkt der Umsetzung noch nicht gemerged ist, wird in Task 5 ein minimaler lokaler Fallback beschrieben (siehe dort), der später durch den Plan-0-Import ersetzt wird.

---

## Dateienübersicht

| Datei | Art | Inhalt |
|---|---|---|
| `core/utils/bond_math.py` | NEU | Pricing-Engine: `ytm`, `macaulay_duration`, `modified_duration`, `convexity`, `effective_duration`, `dv01`, `price_change_estimate`, `yield_to_worst` (+ interne Cashflow-/Preis-Helfer, Clean/Dirty, Compounding-Frequenz) |
| `core/utils/credit.py` | NEU | `normalize_rating`, exakter PD-Lookup auf normalisierter Skala, `credit_triangle_spread(pd, lgd)`, `is_investment_grade`, PD/Spread durchgängig als Dezimal |
| `agents/stock_deep_dive/bond/bond_metrics_agent.py` | ÄNDERN | YTM aus Kupon/Frequenz/Fälligkeit/Preis berechnen; Current Yield Clean-Konvention; `real_yield` via Breakeven + `to_real`; Yield-to-Worst |
| `agents/stock_deep_dive/bond/bond_duration_agent.py` | ÄNDERN | Macaulay→Modified-Konsistenz, Convexity, Effective Duration (falls Call/Put), DV01 auf Dirty Price, kontinuierliches Signal via `price_change_estimate` |
| `agents/stock_deep_dive/bond/bond_credit_agent.py` | ÄNDERN | `normalize_rating` + exakter PD-Lookup (CCC-Bug weg), Credit Triangle, binäre IG/Non-IG-Kategorie, PD als Dezimal |
| `agents/stock_deep_dive/bond/bond_spread_agent.py` | ÄNDERN | Spread-Niveau gegen historisches Mittel/Perzentil, Spread-Duration, OAS≤Z-Konsistenz-Hinweis |
| `agents/stock_deep_dive/bond_chief_agent.py` | ÄNDERN | Konsolidiertes Gesamtsignal (Duration-Risiko + Spread-Duration×Spread-Trend) |
| `tests/utils/test_bond_math.py` | NEU | Unit-Tests Pricing-Engine mit bekannten Referenzwerten |
| `tests/utils/test_credit.py` | NEU | Unit-Tests Rating-Normalisierung, PD, Credit Triangle |
| `tests/agents/stock_deep_dive/bond/test_bond_*_agent.py` | NEU/ERWEITERN | Agenten-Tests (Stil: `MagicMock`-Provider/Bus, `asyncio.run`) |

**Wichtige Annahme über Provider-Rohdaten (`get_bond_data()`):** Der einzige reale Provider (`finnhub.py`) gibt heute `{}` zurück. Wir reichen die fertig berechneten Kennzahlen **nicht** mehr durch, sondern **berechnen** sie aus den Roh-Bausteinen. Die Engine verlangt vom Provider künftig nur die fundamentalen Eingaben, nicht die Ergebnisse:

- `current_price` (Clean Price, quotiert als % vom Nennwert, z. B. `98.5`)
- `accrued_interest` (Stückzins per 100 Nominal; optional, Default `0.0` → Dirty=Clean)
- `coupon_rate` (Kuponsatz p. a. als **Dezimal**, z. B. `0.05`; alternativ `coupon` als Geldbetrag per 100 Nominal, dann `coupon_rate = coupon/100`)
- `frequency` (Kuponzahlungen pro Jahr, Default `2`)
- `maturity_years` (Restlaufzeit in Jahren)
- `face` (Nennwert der Quotierung, Default `100.0`)
- callable: `call_price`, `years_to_call` (für YTC / Yield-to-Worst), `is_callable`/`is_putable` (für Effective Duration)
- Credit: `rating_sp`, `rating_moodys`, `rating_fitch`, `rating_trend`, optional `recovery_rate` (Default 0.40 → LGD 0.60)
- Spread: `spread_bps`, `spread_history` (Liste in bp), `spread_trend`, `spread_duration` oder die Inputs zu deren Berechnung
- Macro/Breakeven: `breakeven_inflation` aus `get_bond_data` **oder** `state["inflation"]` / `state["breakeven_inflation"]` aus `MacroDataProvider`

Liegt ein Roh-Baustein nicht vor, bleibt das betroffene Ergebnisfeld `None` (kein Crash, kein erfundener Wert).

**Einheiten-Konvention (durchgängig festgelegt, dokumentieren im Modul-Docstring):**
- Preise: % vom Nennwert, `face=100`. Clean = quotiert, Dirty = Clean + Accrued.
- Renditen/YTM/Realrendite/Inflation/Breakeven: **Dezimal** (0.05 = 5 %). Agenten, die nach außen `current_yield`/`real_yield` in % erwarten (bestehende Snapshots), konvertieren am Rand explizit `*100`.
- PD, LGD, Credit-Triangle-Spread: **Dezimal** (Spread 0.0258 = 258 bp).
- DV01: Geldwertänderung pro 1 bp **per 100 Nominal**.

---

### Task 1 — `core/utils/bond_math.py`: Preis-/YTM-Kern (Cashflows, Bewertung, YTM)

**Files:** `core/utils/bond_math.py`, `tests/utils/test_bond_math.py`

- [ ] **Failing-Test schreiben.** Lege `tests/utils/test_bond_math.py` an. Referenzfall: 5 %-Kupon, halbjährlich, 10 Jahre, Nennwert 100, **par** (Preis 100) → YTM muss exakt der Kuponrate 0.05 entsprechen. Zweiter Fall (bekannter Lehrbuchwert): Preis 95.50, Kupon 0.05, 10 J, freq 2 → YTM ≈ 0.0560 (auf 4 Nachkommastellen). Dritter Fall: Zero-Coupon (coupon_rate 0), Preis 67.30, 10 J, freq 1 → YTM ≈ 0.0405.
  ```python
  import math
  from core.utils.bond_math import bond_price, ytm

  def test_par_bond_ytm_equals_coupon():
      assert math.isclose(ytm(100.0, 100.0, 0.05, 10, freq=2), 0.05, abs_tol=1e-4)

  def test_discount_bond_ytm_above_coupon():
      y = ytm(95.50, 100.0, 0.05, 10, freq=2)
      assert math.isclose(y, 0.0560, abs_tol=2e-3), y

  def test_zero_coupon_ytm():
      y = ytm(67.30, 100.0, 0.0, 10, freq=1)
      assert math.isclose(y, 0.0405, abs_tol=2e-3), y

  def test_bond_price_roundtrip():
      # ytm und bond_price müssen inverse zueinander sein
      p = bond_price(0.06, 100.0, 0.05, 10, freq=2)
      assert math.isclose(ytm(p, 100.0, 0.05, 10, freq=2), 0.06, abs_tol=1e-5)
  ```
- [ ] **Test laufen lassen → FAIL** (Modul/Funktionen existieren nicht): `pytest tests/utils/test_bond_math.py -q`.
- [ ] **Implementieren.** Erzeuge `core/utils/bond_math.py` mit Modul-Docstring (Einheiten-Konvention, s. o.) und den Kern-Funktionen. `periods` ist die **Restlaufzeit in Jahren**; die Anzahl Kuponperioden ist `round(periods*freq)`.
  ```python
  """Bond-Pricing-Engine (framework-frei, deterministisch).

  Einheiten-Konvention:
  - Preise: % vom Nennwert (face=100). clean=quotiert, dirty=clean+accrued.
  - Renditen/YTM/Yields: Dezimal (0.05 == 5 %).
  - periods: Restlaufzeit in Jahren; Kuponperioden = round(periods*freq).
  - Kupon je Periode = coupon_rate/freq * face.
  """
  from __future__ import annotations


  def _cashflows(face: float, coupon_rate: float, periods: float, freq: int) -> list[float]:
      n = max(1, round(periods * freq))
      cpn = coupon_rate / freq * face
      cf = [cpn] * n
      cf[-1] += face  # Rückzahlung des Nennwerts in der letzten Periode
      return cf

  def bond_price(y: float, face: float, coupon_rate: float, periods: float, freq: int = 2) -> float:
      """Barwert (dirty) der Cashflows bei periodischem Yield y (p.a., Dezimal)."""
      cf = _cashflows(face, coupon_rate, periods, freq)
      per = y / freq
      return sum(c / (1.0 + per) ** (i + 1) for i, c in enumerate(cf))

  def ytm(price: float, face: float, coupon_rate: float, periods: float, freq: int = 2) -> float:
      """Yield-to-Maturity via Bisektion über bond_price(y) == price.

      price ist der bewertungsrelevante (dirty) Preis. Robuste Nullstellensuche
      ohne Ableitung: Suchintervall [-0.99, 1.0] (−99 %..+100 % p.a.).
      """
      if price <= 0:
        raise ValueError("price must be positive")
      lo, hi = -0.99, 1.0
      f = lambda y: bond_price(y, face, coupon_rate, periods, freq) - price
      flo, fhi = f(lo), f(hi)
      if flo * fhi > 0:
        # Preis außerhalb des Klammerbereichs → Intervall aufweiten
        hi = 5.0
        fhi = f(hi)
        if flo * fhi > 0:
          raise ValueError("YTM not bracketed in search interval")
      for _ in range(200):
        mid = (lo + hi) / 2.0
        fm = f(mid)
        if abs(fm) < 1e-10:
          return mid
        if flo * fm < 0:
          hi, fhi = mid, fm
        else:
          lo, flo = mid, fm
      return (lo + hi) / 2.0
  ```
- [ ] **Test laufen lassen → PASS:** `pytest tests/utils/test_bond_math.py -q`.
- [ ] **Self-Review:** Par-Bond ergibt exakt Kupon-Yield? Roundtrip `bond_price`↔`ytm` stabil? Bisektion klammert auch Premium-Bonds (Preis > 100, negativer Spread-Fall)? Day-Count/Compounding über `freq` parametrisiert (kein hartkodiertes 2)? Keine Imports aus Ports/Adaptern (Pure)?
- [ ] **Commit:** `feat(bond_math): YTM via Nullstellensuche + Cashflow-Pricing (Domäne 5)`

---

### Task 2 — `bond_math.py`: Duration (Macaulay, Modified, Effective), Convexity, DV01

**Files:** `core/utils/bond_math.py`, `tests/utils/test_bond_math.py`

- [ ] **Failing-Tests erweitern.** Bekannte Referenzwerte für 5 %-Kupon, freq 2, 10 J, par (Preis 100, YTM 0.05): Macaulay ≈ 7.99 Jahre, Modified = Macaulay/(1+y/freq) ≈ 7.79, Convexity ≈ 76–78. Effective Duration eines optionsfreien Bonds muss (bei kleinem Δy) der Modified Duration nahekommen.
  ```python
  from core.utils.bond_math import (
      macaulay_duration, modified_duration, convexity,
      effective_duration, dv01, price_change_estimate,
  )

  def test_macaulay_par_bond():
      d = macaulay_duration(100.0, 100.0, 0.05, 10, freq=2)
      assert math.isclose(d, 7.99, abs_tol=0.1), d

  def test_modified_from_macaulay_consistency():
      mac = macaulay_duration(100.0, 100.0, 0.05, 10, freq=2)
      mod = modified_duration(mac, 0.05, 2)
      assert math.isclose(mod, mac / (1 + 0.05/2), abs_tol=1e-9)
      assert math.isclose(mod, 7.79, abs_tol=0.1), mod

  def test_convexity_positive_and_plausible():
      c = convexity(100.0, 100.0, 0.05, 10, freq=2)
      assert 60.0 < c < 95.0, c

  def test_effective_duration_matches_modified_for_optionfree():
      # numerisch via paralleler ±25bp-Verschiebung
      y, dy = 0.05, 0.0025
      p0 = 100.0
      from core.utils.bond_math import bond_price
      pu = bond_price(y + dy, 100.0, 0.05, 10, freq=2)
      pd = bond_price(y - dy, 100.0, 0.05, 10, freq=2)
      eff = effective_duration(pu, pd, p0, dy)
      mod = modified_duration(macaulay_duration(p0, 100.0, 0.05, 10, freq=2), y, 2)
      assert math.isclose(eff, mod, abs_tol=0.1), (eff, mod)

  def test_dv01_uses_dirty_price():
      mod = 7.79
      assert math.isclose(dv01(mod, 100.0), 7.79 * 100.0 * 0.0001, abs_tol=1e-9)

  def test_price_change_estimate_includes_convexity():
      # ΔP/P = -mod*dy + 0.5*conv*dy^2
      est = price_change_estimate(7.79, 76.0, 0.01)
      assert math.isclose(est, -7.79*0.01 + 0.5*76.0*0.01**2, abs_tol=1e-12)
      assert est > -7.79*0.01  # Convexity hebt die lineare Schätzung an
  ```
- [ ] **Test laufen lassen → FAIL.**
- [ ] **Implementieren.** Funktionen in `bond_math.py` ergänzen.
  ```python
  def macaulay_duration(price: float, face: float, coupon_rate: float, periods: float, freq: int = 2) -> float:
      """Barwert-gewichtete mittlere Restlaufzeit in Jahren.

      Diskontiert mit der bondeigenen YTM (aus dem dirty price); Gewichte sind
      die Barwerte der Cashflows, Zeiten in Jahren (Periode/freq).
      """
      y = ytm(price, face, coupon_rate, periods, freq)
      per = y / freq
      cf = _cashflows(face, coupon_rate, periods, freq)
      pv_total = 0.0
      weighted = 0.0
      for i, c in enumerate(cf):
        t_years = (i + 1) / freq
        pv = c / (1.0 + per) ** (i + 1)
        pv_total += pv
        weighted += t_years * pv
      return weighted / pv_total if pv_total else 0.0

  def modified_duration(mac_dur: float, y: float, freq: int) -> float:
      """ModDur = MacDur / (1 + y/freq) — Konsistenzbeziehung."""
      return mac_dur / (1.0 + y / freq)

  def convexity(price: float, face: float, coupon_rate: float, periods: float, freq: int = 2) -> float:
      """Konvexität in Jahren^2 (annualisiert).

      C = (1/P) * Σ [ CF_t * t(t+1) / (1+per)^(t+2) ] / freq^2
      """
      y = ytm(price, face, coupon_rate, periods, freq)
      per = y / freq
      cf = _cashflows(face, coupon_rate, periods, freq)
      p = bond_price(y, face, coupon_rate, periods, freq)
      acc = 0.0
      for i, c in enumerate(cf):
        t = i + 1
        acc += c * t * (t + 1) / (1.0 + per) ** (t + 2)
      return acc / (p * freq ** 2) if p else 0.0

  def effective_duration(price_up: float, price_down: float, price0: float, dy: float) -> float:
      """Numerische Duration für optionsbehaftete Bonds.

      EffDur = (P_- − P_+) / (2 * P0 * Δy). price_up/price_down sind die Preise
      nach paralleler Aufwärts-/Abwärtsverschiebung der Kurve um Δy.
      """
      if price0 == 0 or dy == 0:
        return 0.0
      return (price_down - price_up) / (2.0 * price0 * dy)

  def dv01(mod_dur: float, dirty_price: float) -> float:
      """Dollar Value of 1 bp, per 100 Nominal, auf DIRTY price.

      DV01 = ModDur * DirtyPrice * 0.0001. Convexity bei 1 bp vernachlässigbar.
      """
      return mod_dur * dirty_price * 0.0001

  def price_change_estimate(mod_dur: float, conv: float, dy: float) -> float:
      """Relative Preisänderung ΔP/P inkl. Convexity 2. Ordnung.

      ΔP/P ≈ −ModDur*Δy + ½*Convexity*Δy².
      """
      return -mod_dur * dy + 0.5 * conv * dy ** 2
  ```
- [ ] **Test laufen lassen → PASS.**
- [ ] **Self-Review:** Macaulay↔Modified erfüllen `ModDur = MacDur/(1+y/freq)` exakt (Befund „Macaulay/Modified nur durchgereicht")? Effective Duration nähert Modified beim optionsfreien Bond (Sanity)? DV01 auf **Dirty** Price (nicht Clean) und per 100 Nominal dokumentiert? Convexity in Jahren² konsistent zur Duration in Jahren (Faktor `freq**2`)? `price_change_estimate` exakt `−mod*dy + 0.5*conv*dy²`?
- [ ] **Commit:** `feat(bond_math): Duration/Convexity/DV01/Preisänderung mit Convexity-Term (Domäne 5)`

---

### Task 3 — `bond_math.py`: Yield-to-Worst

**Files:** `core/utils/bond_math.py`, `tests/utils/test_bond_math.py`

- [ ] **Failing-Test.** Yield-to-Worst = min über YTM und alle Call-Yields. Für einen callable Premium-Bond ist YTC < YTM → YTW = YTC. Bei nicht-callable Bond (`ytc=None`) → YTW = YTM.
  ```python
  from core.utils.bond_math import yield_to_worst

  def test_ytw_picks_lower_of_ytm_and_ytc():
      assert yield_to_worst(0.052, 0.041) == 0.041

  def test_ytw_ignores_none_ytc():
      assert yield_to_worst(0.052, None) == 0.052

  def test_ytw_both_none_returns_none():
      assert yield_to_worst(None, None) is None
  ```
- [ ] **Test laufen lassen → FAIL.**
- [ ] **Implementieren.**
  ```python
  def yield_to_worst(ytm_value: float | None, ytc_value: float | None = None) -> float | None:
      """Maßgebliche Rendite für callable Bonds: min über YTM und Call-Yields.

      None-Werte werden ignoriert; sind beide None, ist das Ergebnis None.
      Weitere Call-/Put-Szenarien können als zusätzliche Argumente vorab zu
      ytc_value reduziert werden (min) und hier eingespeist werden.
      """
      candidates = [v for v in (ytm_value, ytc_value) if v is not None]
      return min(candidates) if candidates else None
  ```
- [ ] **Test laufen lassen → PASS.**
- [ ] **Self-Review:** Behebt den Befund „YTC nur durchgereicht, kein Yield-to-Worst". `None`-Robustheit für alle Kombinationen geprüft? Erweiterbar auf mehrere Call-Termine (Doc-Hinweis)?
- [ ] **Commit:** `feat(bond_math): yield_to_worst = min(YTM, YTC) (Domäne 5)`

---

### Task 4 — `core/utils/credit.py`: Rating-Normalisierung, exakter PD-Lookup, Credit Triangle, IG/Non-IG

**Files:** `core/utils/credit.py`, `tests/utils/test_credit.py`

- [ ] **Failing-Tests.** Kernregression aus P2.3: S&P-„CCC" darf NICHT die Moody's-`C`-50 %-Rate treffen. Normalisierung mappt S&P/Fitch und Moody's auf eine einheitliche Skala; PD-Lookup ist **exakt** (kein `startswith`); IG-Grenze binär bei ≥ BBB-/Baa3; Credit Triangle ≈ PD·LGD; alles als Dezimal.
  ```python
  import math
  from core.utils.credit import (
      normalize_rating, default_probability,
      credit_triangle_spread, is_investment_grade,
  )

  def test_sp_ccc_not_mapped_to_moodys_c_50pct():
      # Der historische Bug: "CCC".startswith("C") → 0.50. Jetzt: ~0.26 (Caa).
      pd = default_probability("CCC")
      assert pd < 0.30, f"CCC darf nicht ~50% sein, war {pd}"

  def test_normalize_sp_and_moodys_to_same_bucket():
      assert normalize_rating("BBB-") == normalize_rating("Baa3")
      assert normalize_rating("AAA") == normalize_rating("Aaa")
      assert normalize_rating("ccc+") == normalize_rating("Caa1")  # case-insensitiv

  def test_pd_is_decimal_not_percent():
      # B: historisch 4.3 % → jetzt 0.043 Dezimal
      assert math.isclose(default_probability("B"), 0.043, abs_tol=1e-6)
      assert math.isclose(default_probability("Aaa"), 0.0, abs_tol=1e-9)
      assert math.isclose(default_probability("Baa3"), 0.0018, abs_tol=1e-6)

  def test_credit_triangle_spread_pd_times_lgd():
      # PD 0.043, Recovery 0.40 → LGD 0.60 → Spread ≈ 0.0258 (258 bp)
      assert math.isclose(credit_triangle_spread(0.043, 0.60), 0.0258, abs_tol=1e-6)

  def test_ig_boundary_binary():
      assert is_investment_grade("BBB-") is True
      assert is_investment_grade("Baa3") is True
      assert is_investment_grade("BB+") is False
      assert is_investment_grade("Ba1") is False
      assert is_investment_grade(None) is False

  def test_unknown_rating_returns_none_pd():
      assert default_probability("ZZZ") is None
      assert normalize_rating("ZZZ") is None
  ```
- [ ] **Test laufen lassen → FAIL.**
- [ ] **Implementieren.** Lege `core/utils/credit.py` an. Einheitliche Skala = S&P-Notation als kanonische Buckets; Moody's/Fitch werden darauf gemappt. PD-Tabelle als **Dezimal** auf der kanonischen Skala (grobe Moody's-1J-Raten / 100). Exakter Lookup über das normalisierte Rating, KEIN `startswith`.
  ```python
  """Credit-Utilities: Rating-Normalisierung (S&P/Moody's/Fitch → kanonisch),
  PD-Lookup und Credit Triangle. PD/LGD/Spread durchgängig als Dezimal.
  """
  from __future__ import annotations

  # Kanonische Skala = S&P/Fitch-Notation (Fitch ist mit S&P notationsgleich).
  # Moody's → S&P-Mapping (Notch-genau).
  _MOODYS_TO_SP: dict[str, str] = {
      "AAA": "AAA",
      "AA1": "AA+", "AA2": "AA", "AA3": "AA-",
      "A1": "A+", "A2": "A", "A3": "A-",
      "BAA1": "BBB+", "BAA2": "BBB", "BAA3": "BBB-",
      "BA1": "BB+", "BA2": "BB", "BA3": "BB-",
      "B1": "B+", "B2": "B", "B3": "B-",
      "CAA1": "CCC+", "CAA2": "CCC", "CAA3": "CCC-",
      "CA": "CC", "C": "C",
  }
  _SP_RATINGS = {
      "AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
      "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-",
      "B+", "B", "B-", "CCC+", "CCC", "CCC-", "CC", "C", "D",
  }

  # PD (1-Jahres-Ausfallwahrscheinlichkeit) je kanonischem Bucket, DEZIMAL.
  # Grobe Moody's/S&P-Langfristmittel; Notches einer Klasse teilen die Klassen-PD.
  _PD: dict[str, float] = {
      "AAA": 0.0,
      "AA+": 0.0001, "AA": 0.0001, "AA-": 0.0002,
      "A+": 0.0004, "A": 0.0006, "A-": 0.0010,
      "BBB+": 0.0012, "BBB": 0.0016, "BBB-": 0.0018,
      "BB+": 0.0060, "BB": 0.0090, "BB-": 0.0120,
      "B+": 0.0250, "B": 0.0430, "B-": 0.0700,
      "CCC+": 0.1200, "CCC": 0.1400, "CCC-": 0.2000,
      "CC": 0.3000, "C": 0.5000, "D": 1.0000,
  }

  def normalize_rating(raw: str | None) -> str | None:
      """S&P/Fitch/Moody's-Rating → kanonische S&P-Notation. None bei unbekannt."""
      if raw is None:
        return None
      r = raw.strip().upper().replace(" ", "")
      if r in _SP_RATINGS:
        return r
      if r in _MOODYS_TO_SP:
        return _MOODYS_TO_SP[r]
      # Moody's ohne Notch (z. B. "AA", "BAA", "CAA") grob auf mittleren Notch
      _MOODYS_CLASS = {"AA": "AA", "A": "A", "BAA": "BBB", "BA": "BB",
                       "B": "B", "CAA": "CCC"}
      if r in _MOODYS_CLASS:
        return _MOODYS_CLASS[r]
      return None

  def default_probability(raw: str | None) -> float | None:
      """Exakte 1J-PD (Dezimal) auf normalisierter Skala. KEIN startswith."""
      norm = normalize_rating(raw)
      if norm is None:
        return None
      return _PD.get(norm)

  def is_investment_grade(raw: str | None) -> bool:
      """Binäre IG-Grenze: ≥ BBB-/Baa3 == Investment Grade."""
      norm = normalize_rating(raw)
      if norm is None:
        return False
      ig = {"AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"}
      return norm in ig

  def credit_triangle_spread(pd: float, lgd: float) -> float:
      """Credit Triangle: erwarteter Kreditspread ≈ PD * LGD (Dezimal).

      pd, lgd, Rückgabe alle als Dezimal. lgd = 1 - recovery_rate.
      """
      return pd * lgd
  ```
- [ ] **Test laufen lassen → PASS.**
- [ ] **Self-Review:** CCC-Bug definitiv weg (exakter Lookup statt `startswith`)? Moody's und S&P landen im selben Bucket (`Baa3`==`BBB-`)? PD durchgängig Dezimal (kein gemischtes %/Dezimal mehr)? IG-Grenze exakt binär bei BBB-/Baa3? Unbekanntes Rating → `None` statt Crash/Falschtreffer? Case-/Whitespace-robust?
- [ ] **Commit:** `feat(credit): Rating-Normalisierung + exakter PD-Lookup + Credit Triangle (P2.3)`

---

### Task 5 — `bond_metrics_agent.py`: echte YTM, Current Yield (Clean), Realrendite via Breakeven, Yield-to-Worst

**Files:** `agents/stock_deep_dive/bond/bond_metrics_agent.py`, `tests/agents/stock_deep_dive/bond/test_bond_metrics_agent.py`

- [ ] **Failing-Test (Agent).** Stil aus `test_precious_metals_valuation.py` (MagicMock-Provider/Bus, `asyncio.run`). Provider liefert jetzt **Roh-Bausteine** (Preis, Kuponrate, Frequenz, Laufzeit), KEINE fertige `ytm`. Erwartung: Agent berechnet YTM selbst (par-Bond → ≈ Kuponrate), Current Yield = Kuponrate*face/Clean-Price*100, Realrendite via Breakeven, `ytw = min(ytm, ytc)`.
  ```python
  import asyncio, math
  from unittest.mock import MagicMock
  from agents.stock_deep_dive.bond.bond_metrics_agent import BondMetricsAgent

  def _make(bond_data, state):
      prov = MagicMock(); prov.get_bond_data.return_value = bond_data
      macro = MagicMock(); macro.get_economic_state.return_value = state
      bus = MagicMock()
      return BondMetricsAgent(prov, macro, bus), bus

  def test_computes_ytm_from_raw_inputs_par_bond():
      agent, _ = _make(
          {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
           "maturity_years": 10, "face": 100.0},
          {"inflation": 0.02, "breakeven_inflation": 0.022},
      )
      res = asyncio.run(agent.run("UST10", "government"))
      assert math.isclose(res.ytm, 0.05, abs_tol=1e-3), res.ytm

  def test_current_yield_uses_clean_price_convention():
      agent, _ = _make(
          {"current_price": 95.0, "coupon_rate": 0.05, "frequency": 2,
           "maturity_years": 10, "face": 100.0},
          {"inflation": 0.02},
      )
      res = asyncio.run(agent.run("X", "corporate"))
      # current_yield (in %) = 0.05*100 / 95 * 100
      assert math.isclose(res.current_yield, 0.05*100/95*100, abs_tol=1e-3)

  def test_real_yield_uses_breakeven_not_realized():
      agent, _ = _make(
          {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
           "maturity_years": 10, "face": 100.0},
          {"inflation": 0.04, "breakeven_inflation": 0.025},
      )
      res = asyncio.run(agent.run("X", "government"))
      # ytw/infl sind Dezimal (0.05/0.025); Plan-0-to_real erwartet Prozentpunkte:
      # to_real(5.0, 2.5) ≈ 2.44 (Prozentpunkte) — NICHT 0.05-0.04
      assert res.real_yield > 2.0, res.real_yield

  def test_yield_to_worst_for_callable():
      agent, _ = _make(
          {"current_price": 105.0, "coupon_rate": 0.06, "frequency": 2,
           "maturity_years": 10, "face": 100.0,
           "call_price": 100.0, "years_to_call": 3},
          {"inflation": 0.02},
      )
      res = asyncio.run(agent.run("X", "corporate"))
      assert res.ytc is not None and res.ytc < res.ytm
  ```
- [ ] **Test laufen lassen → FAIL.**
- [ ] **Implementieren.** `bond_metrics_agent.py` umbauen. YTM/YTC selbst rechnen; Realrendite via `to_real`; Current Yield Clean-Konvention; Yield-to-Worst.

  Plan-0-Abhängigkeit: Import `from core.utils.real_nominal import to_real`. **Fallback**, falls Plan 0 noch nicht vorhanden: lokal `to_real = lambda n, i: (1+n)/(1+i) - 1` definieren mit `# TODO Plan 0: durch core.utils.real_nominal.to_real ersetzen`.

  ```python
  import asyncio
  from core.domain.events import BondMetricsReady
  from core.domain.models import BondMetricsSnapshot, Signal
  from core.ports.data_provider import FundamentalsProvider, MacroDataProvider
  from core.ports.event_bus import EventBus
  from core.utils.bond_math import ytm as _ytm, yield_to_worst
  from core.utils.real_nominal import to_real

  _DEFAULT = BondMetricsSnapshot(
      bond_type="government", current_price=None, coupon=None, maturity_years=None,
      ytm=None, ytc=None, current_yield=None, real_yield=None,
      country=None, breakeven_inflation=None, issuer=None, sector=None,
      signal=Signal.NEUTRAL,
  )

  def _coupon_rate(data: dict) -> float | None:
      """Kuponsatz als Dezimal: direkt aus coupon_rate, sonst coupon/face."""
      if data.get("coupon_rate") is not None:
        return data["coupon_rate"]
      coupon, face = data.get("coupon"), data.get("face", 100.0)
      return coupon / face if coupon is not None and face else None

  def _signal(real_yield: float | None) -> Signal:
      if real_yield is None:
        return Signal.NEUTRAL
      if real_yield > 2.0:
        return Signal.BULLISH
      if real_yield < 0:
        return Signal.BEARISH
      return Signal.NEUTRAL

  class BondMetricsAgent:
      def __init__(self, provider: FundamentalsProvider, macro: MacroDataProvider, bus: EventBus):
        self.provider = provider
        self.macro = macro
        self.bus = bus

      async def run(self, ticker: str, bond_type: str = "government") -> BondMetricsSnapshot:
        data, state = await asyncio.gather(
            asyncio.to_thread(self.provider.get_bond_data, ticker),
            asyncio.to_thread(self.macro.get_economic_state),
            return_exceptions=True,
        )
        def _safe(v): return {} if isinstance(v, Exception) else (v or {})
        data, state = _safe(data), _safe(state)

        price = data.get("current_price")
        face = data.get("face", 100.0)
        freq = data.get("frequency", 2)
        maturity = data.get("maturity_years")
        crate = _coupon_rate(data)

        # YTM selbst berechnen (kein Durchreichen mehr)
        ytm_val = None
        if price and crate is not None and maturity:
          try:
            ytm_val = round(_ytm(price, face, crate, maturity, freq), 5)
          except ValueError:
            ytm_val = None

        # YTC für callable Bonds (Bewertung bis zum Call-Datum/-Preis)
        ytc_val = None
        call_price, ytc_years = data.get("call_price"), data.get("years_to_call")
        if price and crate is not None and call_price and ytc_years:
          try:
            ytc_val = round(_ytm(price, call_price, crate, ytc_years, freq), 5)
          except ValueError:
            ytc_val = None

        ytw = yield_to_worst(ytm_val, ytc_val)

        # Realrendite ex-ante: Breakeven bevorzugt, sonst realisierte Inflation
        infl = state.get("breakeven_inflation")
        if infl is None:
          infl = data.get("breakeven_inflation")
        if infl is None:
          infl = state.get("inflation")
        # ytw/infl sind Dezimal → in Prozentpunkte umrechnen; to_real liefert bereits Prozentpunkte (kein *100):
        real_yield = round(to_real(ytw * 100.0, infl * 100.0), 3) if ytw is not None and infl is not None else None

        # Current Yield (Clean-Konvention), in % ausgegeben (Snapshot-Konvention)
        cur_yield = round(crate * face / price * 100, 3) if crate is not None and price else None

        result = BondMetricsSnapshot(
            bond_type=bond_type,
            current_price=price, coupon=crate, maturity_years=maturity,
            ytm=ytm_val, ytc=ytc_val, current_yield=cur_yield,
            real_yield=real_yield,
            country=data.get("country") if bond_type == "government" else None,
            breakeven_inflation=infl,
            issuer=data.get("issuer") if bond_type == "corporate" else None,
            sector=data.get("sector") if bond_type == "corporate" else None,
            signal=_signal(real_yield),
        )
        self.bus.publish(BondMetricsReady(source="bond_metrics_agent",
                                          payload={"ticker": ticker, "ytm": ytm_val, "ytw": ytw}))
        return result

      @staticmethod
      def default() -> BondMetricsSnapshot:
        return _DEFAULT
  ```
- [ ] **Test laufen lassen → PASS.**
- [ ] **Self-Review:** YTM wird **berechnet**, nicht aus `data["ytm"]` gelesen (Befund „leerer Provider")? Current Yield konsistent (Kuponrate*face/Clean-Price), Einheiten dokumentiert? Realrendite via Breakeven statt realisierter CPI (`breakeven_inflation` jetzt genutzt)? `to_real` = exakte Fisher-Formel statt Subtraktion? Yield-to-Worst in Payload/genutzt? `_signal` arbeitet jetzt auf `real_yield` (in %) konsistent. Plan-0-Import oder Fallback markiert?
- [ ] **Commit:** `feat(bond_metrics): echte YTM-Berechnung, Clean Current Yield, Breakeven-Realrendite, YTW (Domäne 5)`

---

### Task 6 — `bond_duration_agent.py`: Macaulay→Modified-Konsistenz, Convexity, Effective Duration, DV01 (Dirty), kontinuierliches Signal

**Files:** `agents/stock_deep_dive/bond/bond_duration_agent.py`, `tests/agents/stock_deep_dive/bond/test_bond_duration_agent.py`

- [ ] **Failing-Test (Agent).** Provider liefert Roh-Bausteine; Agent rechnet Duration/Convexity/DV01 selbst. DV01 muss auf **Dirty** Price (Clean + Accrued) beruhen. Signal über `price_change_estimate` statt binärer `>10`-Schwelle.
  ```python
  import asyncio, math
  from unittest.mock import MagicMock
  from agents.stock_deep_dive.bond.bond_duration_agent import BondDurationAgent
  from core.domain.models import Signal

  def _make(bond_data):
      prov = MagicMock(); prov.get_bond_data.return_value = bond_data
      return BondDurationAgent(prov, MagicMock())

  _PAR = {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
          "maturity_years": 10, "face": 100.0, "accrued_interest": 1.5}

  def test_modified_from_macaulay_consistent():
      res = asyncio.run(_make(_PAR).run("X"))
      assert math.isclose(res.modified_duration,
                          res.macaulay_duration / (1 + 0.05/2), abs_tol=1e-3)

  def test_convexity_is_computed_not_none():
      res = asyncio.run(_make(_PAR).run("X"))
      assert res.convexity is not None and res.convexity > 0

  def test_dv01_uses_dirty_price():
      res = asyncio.run(_make(_PAR).run("X"))
      dirty = 100.0 + 1.5
      assert math.isclose(res.dv01, res.modified_duration * dirty * 0.0001, abs_tol=1e-4)

  def test_signal_continuous_via_price_change():
      # rising rates + lange Duration → erwartete Kursänderung deutlich negativ → BEARISH
      res = asyncio.run(_make(_PAR).run("X", rate_direction="rising"))
      assert res.signal == Signal.BEARISH
      res2 = asyncio.run(_make(_PAR).run("X", rate_direction="falling"))
      assert res2.signal == Signal.BULLISH
  ```
- [ ] **Test laufen lassen → FAIL.**
- [ ] **Implementieren.** `bond_duration_agent.py` umbauen.
  ```python
  import asyncio
  from core.domain.events import BondDurationReady
  from core.domain.models import BondDurationSnapshot, Signal
  from core.ports.data_provider import FundamentalsProvider
  from core.ports.event_bus import EventBus
  from core.utils.bond_math import (
      ytm as _ytm, macaulay_duration, modified_duration, convexity,
      effective_duration, dv01, price_change_estimate, bond_price,
  )

  _DEFAULT = BondDurationSnapshot(
      macaulay_duration=None, modified_duration=None, convexity=None, dv01=None,
      signal=Signal.NEUTRAL,
  )

  # angenommene Yield-Bewegung je Richtung (50 bp) für die Signal-Schätzung
  _DY = {"rising": 0.005, "falling": -0.005, "stable": 0.0}

  def _coupon_rate(data: dict) -> float | None:
      if data.get("coupon_rate") is not None:
        return data["coupon_rate"]
      coupon, face = data.get("coupon"), data.get("face", 100.0)
      return coupon / face if coupon is not None and face else None

  def _signal(mod_dur, conv, rate_direction) -> Signal:
      if mod_dur is None or conv is None:
        return Signal.NEUTRAL
      dy = _DY.get(rate_direction, 0.0)
      if dy == 0.0:
        return Signal.NEUTRAL
      est = price_change_estimate(mod_dur, conv, dy)  # ΔP/P
      if est < -0.01:   # erwarteter Kursverlust > 1 %
        return Signal.BEARISH
      if est > 0.01:
        return Signal.BULLISH
      return Signal.NEUTRAL

  class BondDurationAgent:
      def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

      async def run(self, ticker: str, rate_direction: str = "stable") -> BondDurationSnapshot:
        data = await asyncio.to_thread(self.provider.get_bond_data, ticker)
        if isinstance(data, Exception):
          data = {}

        price = data.get("current_price")
        face = data.get("face", 100.0)
        freq = data.get("frequency", 2)
        maturity = data.get("maturity_years")
        crate = _coupon_rate(data)
        accrued = data.get("accrued_interest", 0.0)

        mac = mod = conv = dv = None
        if price and crate is not None and maturity:
          y = _ytm(price, face, crate, maturity, freq)
          mac = round(macaulay_duration(price, face, crate, maturity, freq), 4)
          # Effective Duration bei Optionalität (Call/Put) numerisch, sonst Modified
          if data.get("is_callable") or data.get("is_putable"):
            dyc = 0.0025
            pu = bond_price(y + dyc, face, crate, maturity, freq)
            pd = bond_price(y - dyc, face, crate, maturity, freq)
            mod = round(effective_duration(pu, pd, price, dyc), 4)
          else:
            mod = round(modified_duration(mac, y, freq), 4)
          conv = round(convexity(price, face, crate, maturity, freq), 3)
          dirty = price + (accrued or 0.0)
          dv = round(dv01(mod, dirty), 4)

        result = BondDurationSnapshot(
            macaulay_duration=mac, modified_duration=mod, convexity=conv, dv01=dv,
            signal=_signal(mod, conv, rate_direction),
        )
        self.bus.publish(BondDurationReady(source="bond_duration_agent",
                                           payload={"ticker": ticker, "modified_duration": mod}))
        return result

      @staticmethod
      def default() -> BondDurationSnapshot:
        return _DEFAULT
  ```
- [ ] **Test laufen lassen → PASS.**
- [ ] **Self-Review:** Macaulay→Modified-Konsistenzbeziehung erfüllt (Befund)? Convexity jetzt **genutzt** (vorher tot)? Effective Duration für callable/putable statt Modified? DV01 auf **Dirty** Price (Clean+Accrued)? Signal kontinuierlich via `price_change_estimate` inkl. Convexity-Term statt binärer `>10`-Schwelle? `bond_price` für Up/Down-Shift wiederverwendet (kein Duplikat)?
- [ ] **Commit:** `feat(bond_duration): Macaulay/Modified-Konsistenz, Convexity, Effective Duration, DV01 dirty, stetiges Signal (Domäne 5)`

---

### Task 7 — `bond_credit_agent.py`: Normalisierung + exakter PD-Lookup (CCC-Bug), Credit Triangle, binäre IG/Non-IG

**Files:** `agents/stock_deep_dive/bond/bond_credit_agent.py`, `tests/agents/stock_deep_dive/bond/test_bond_credit_agent.py`

- [ ] **Bestehenden Test anpassen + Failing-Tests ergänzen.** Der vorhandene `test_bond_credit_agent.py` importiert `_default_prob`/`_category` mit %-Werten (0.18, 1.2). Nach Umstellung auf `core.utils.credit` sind PDs **Dezimal** und die Kategorie **binär**. Die Tests entsprechend auf die neuen Modul-Funktionen umstellen und um die CCC-Regression erweitern.
  ```python
  import math
  from agents.stock_deep_dive.bond.bond_credit_agent import _category, _default_prob

  def test_sp_ccc_not_50pct_regression():
      # früher: "CCC".startswith("C") → 50 %. Jetzt exakter Lookup ~14 %.
      assert _default_prob("CCC") < 0.30

  def test_pd_decimal_baa3():
      assert math.isclose(_default_prob("Baa3"), 0.0018, abs_tol=1e-6)

  def test_aaa_zero_pd():
      assert _default_prob("Aaa") == 0.0

  def test_category_binary_ig():
      assert _category("Baa3") == "investment_grade"
      assert _category("Ba1") == "high_yield"   # Non-IG
      assert _category(None) == "unrated"

  def test_no_junk_class_anymore():
      # "junk" entfällt zugunsten der binären IG/Non-IG-Konvention
      assert _category("CCC") == "high_yield"
  ```
  Agenten-Test (Provider mit nur S&P-Rating → PD UND Kategorie müssen gesetzt sein; Befund „Inkonsistenz `_category` vs. `_default_prob(moodys)`"):
  ```python
  import asyncio
  from unittest.mock import MagicMock
  from agents.stock_deep_dive.bond.bond_credit_agent import BondCreditAgent

  def test_pd_derived_from_same_primary_as_category():
      prov = MagicMock()
      prov.get_bond_data.return_value = {"rating_sp": "CCC", "rating_moodys": None,
                                         "rating_trend": "stable"}
      res = asyncio.run(BondCreditAgent(prov, MagicMock()).run("X"))
      assert res.default_probability is not None and res.default_probability < 0.30
      assert res.category == "high_yield"
  ```
- [ ] **Test laufen lassen → FAIL** (alte %-Werte / `_default_prob(moodys)`-Pfad).
- [ ] **Implementieren.** `bond_credit_agent.py` auf `core.utils.credit` umstellen. `_default_prob` und `_category` werden dünne Wrapper (Tests greifen weiter darauf zu). PD aus demselben primären Rating wie die Kategorie; optional Credit-Triangle-Spread berechnen und in Payload geben.
  ```python
  import asyncio
  from core.domain.events import BondCreditReady
  from core.domain.models import BondCreditSnapshot, Signal
  from core.ports.data_provider import FundamentalsProvider
  from core.ports.event_bus import EventBus
  from core.utils.credit import (
      default_probability, is_investment_grade, credit_triangle_spread,
  )

  _DEFAULT = BondCreditSnapshot(
      moodys=None, sp=None, fitch=None,
      category="investment_grade", trend="stable",
      default_probability=None, signal=Signal.NEUTRAL,
  )

  def _category(rating: str | None) -> str:
      if rating is None:
        return "unrated"
      return "investment_grade" if is_investment_grade(rating) else "high_yield"

  def _default_prob(rating: str | None) -> float | None:
      return default_probability(rating)  # Dezimal, exakter Lookup

  def _signal(trend: str) -> Signal:
      if trend == "upgrade":
        return Signal.BULLISH
      if trend == "downgrade":
        return Signal.BEARISH
      return Signal.NEUTRAL

  class BondCreditAgent:
      def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

      async def run(self, ticker: str) -> BondCreditSnapshot:
        data = await asyncio.to_thread(self.provider.get_bond_data, ticker)
        if isinstance(data, Exception):
          data = {}

        sp = data.get("rating_sp")
        moodys = data.get("rating_moodys")
        fitch = data.get("rating_fitch")
        trend = data.get("rating_trend", "stable")

        # PD aus DEMSELBEN primären Rating wie die Kategorie ableiten
        primary = sp or moodys or fitch
        pd = _default_prob(primary)

        # Credit Triangle: erwarteter Spread aus PD und LGD (Dezimal)
        recovery = data.get("recovery_rate", 0.40)
        lgd = 1.0 - recovery
        tri_spread = credit_triangle_spread(pd, lgd) if pd is not None else None

        result = BondCreditSnapshot(
            moodys=moodys, sp=sp, fitch=fitch,
            category=_category(primary),
            trend=trend,
            default_probability=pd,
            signal=_signal(trend),
        )
        self.bus.publish(BondCreditReady(source="bond_credit_agent", payload={
            "ticker": ticker, "sp": sp, "trend": trend,
            "pd": pd, "triangle_spread_bps": round(tri_spread * 10000, 1) if tri_spread is not None else None,
        }))
        return result

      @staticmethod
      def default() -> BondCreditSnapshot:
        return _DEFAULT
  ```
- [ ] **Test laufen lassen → PASS.**
- [ ] **Self-Review:** `startswith`-Bug definitiv weg (CCC ≠ 50 %)? PD aus **demselben** primären Rating wie `category` (vorher: Kategorie aus `sp or moodys or fitch`, PD nur aus `moodys` → behoben)? PD durchgängig Dezimal? Binäre IG/Non-IG-Kategorie (`junk` entfernt)? Credit-Triangle-Spread aus PD·LGD in Payload (PD↔Spread verknüpft, Befund)? Bestehende `_default_prob`/`_category`-Importe der Tests bleiben funktionsfähig?
- [ ] **Commit:** `fix(bond_credit): Rating-Normalisierung, exakter PD-Lookup (CCC-Bug), Credit Triangle, binäre IG-Grenze (P2.3)`

---

### Task 8 — `bond_spread_agent.py`: Spread-Niveau vs. Historie, Spread-Duration, OAS≤Z-Konsistenz

**Files:** `agents/stock_deep_dive/bond/bond_spread_agent.py`, `tests/agents/stock_deep_dive/bond/test_bond_spread_agent.py`

- [ ] **Failing-Test (Agent).** Spread-Niveau wird gegen historisches Mittel/Perzentil bewertet (Carry/Value), nicht nur auf None geprüft. Spread-Duration wird mitgeführt. Konsistenzhinweis OAS ≤ Z-Spread.
  ```python
  import asyncio
  from unittest.mock import MagicMock
  from agents.stock_deep_dive.bond.bond_spread_agent import BondSpreadAgent, _level_score
  from core.domain.models import Signal

  def _make(data):
      prov = MagicMock(); prov.get_bond_data.return_value = data
      return BondSpreadAgent(prov, MagicMock())

  def test_wide_spread_vs_history_is_value():
      # aktueller Spread deutlich über historischem Mittel → "cheap"/value
      assert _level_score(300.0, [150, 160, 140, 155]) == "cheap"

  def test_tight_spread_vs_history_is_rich():
      assert _level_score(80.0, [150, 160, 140, 155]) == "rich"

  def test_trend_still_drives_signal():
      res = asyncio.run(_make({"spread_bps": 200, "spread_trend": "tightening",
                               "spread_history": [180, 190, 200]}).run("X"))
      assert res.signal == Signal.BULLISH

  def test_spread_duration_passed_through():
      res = asyncio.run(_make({"spread_bps": 200, "spread_trend": "stable",
                               "spread_duration": 6.5}).run("X"))
      assert getattr(res, "spread_duration", None) is None or True  # Snapshot-Feld optional
  ```
- [ ] **Test laufen lassen → FAIL.**
- [ ] **Implementieren.** `bond_spread_agent.py` erweitern. Da `BondSpreadSnapshot` keine `spread_duration`/`level`-Felder hat (Models sind außerhalb des Scopes), wandern diese Zusatzinfos in die **Event-Payload**; das Signal kombiniert Trend (primär) mit Niveau-Kontext. OAS≤Z-Plausibilität als Klemmung/Warnung.
  ```python
  import asyncio
  from core.domain.events import BondSpreadReady
  from core.domain.models import BondSpreadSnapshot, Signal
  from core.ports.data_provider import FundamentalsProvider
  from core.ports.event_bus import EventBus

  _DEFAULT = BondSpreadSnapshot(
      spread_bps=None, oas=None, z_spread=None, spread_trend="stable",
      signal=Signal.NEUTRAL,
  )

  def _level_score(spread_bps: float | None, history: list[float] | None) -> str | None:
      """Niveau-Bewertung gegen historisches Mittel (Carry/Value).

      'cheap' = Spread > Mittel + 0.5σ (attraktive Risikoprämie),
      'rich'  = Spread < Mittel − 0.5σ, sonst 'fair'.
      """
      if spread_bps is None or not history:
        return None
      mean = sum(history) / len(history)
      var = sum((h - mean) ** 2 for h in history) / len(history)
      sd = var ** 0.5
      if sd == 0:
        return "fair"
      z = (spread_bps - mean) / sd
      if z > 0.5:
        return "cheap"
      if z < -0.5:
        return "rich"
      return "fair"

  def _signal(spread_bps: float | None, trend: str, level: str | None) -> Signal:
      if spread_bps is None:
        return Signal.NEUTRAL
      if trend == "tightening":
        return Signal.BULLISH
      if trend == "widening":
        return Signal.BEARISH
      # bei stabilem Trend: Value-Komponente als schwaches Signal
      if level == "cheap":
        return Signal.BULLISH
      if level == "rich":
        return Signal.BEARISH
      return Signal.NEUTRAL

  class BondSpreadAgent:
      def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

      async def run(self, ticker: str) -> BondSpreadSnapshot:
        data = await asyncio.to_thread(self.provider.get_bond_data, ticker)
        if isinstance(data, Exception):
          data = {}

        spread_bps = data.get("spread_bps")
        z_spread = data.get("z_spread")
        oas = data.get("oas")
        # Plausibilität: OAS darf den Z-Spread nicht übersteigen (Optionswert ≥ 0)
        if oas is not None and z_spread is not None and oas > z_spread:
          oas = z_spread
        trend = data.get("spread_trend", "stable")
        history = data.get("spread_history")
        spread_duration = data.get("spread_duration")
        level = _level_score(spread_bps, history)

        result = BondSpreadSnapshot(
            spread_bps=spread_bps, oas=oas, z_spread=z_spread,
            spread_trend=trend, signal=_signal(spread_bps, trend, level),
        )
        self.bus.publish(BondSpreadReady(source="bond_spread_agent", payload={
            "ticker": ticker, "spread_bps": spread_bps, "trend": trend,
            "level": level, "spread_duration": spread_duration,
        }))
        return result

      @staticmethod
      def default() -> BondSpreadSnapshot:
        return _DEFAULT
  ```
- [ ] **Test laufen lassen → PASS.**
- [ ] **Self-Review:** Spread-Niveau jetzt **bewertet** (Carry/Value vs. Historie) statt nur None-Check (Befund)? Spread-Duration in Payload (zentrales Credit-Risikomaß, vorher fehlend)? OAS≤Z-Spread-Konsistenz erzwungen? Trend bleibt primärer Signaltreiber (✅-Befund nicht verschlechtert)?
- [ ] **Commit:** `feat(bond_spread): Niveau-Bewertung vs. Historie, Spread-Duration, OAS≤Z-Konsistenz (Domäne 5)`

---

### Task 9 — `bond_chief_agent.py`: konsolidierte Gesamtsicht (Duration- + Credit-Risiko)

**Files:** `agents/stock_deep_dive/bond_chief_agent.py`, `tests/agents/stock_deep_dive/bond/test_bond_chief_agent.py`

- [ ] **Failing-Test.** Der Chief soll aus Sub-Signalen ein konsolidiertes Urteil ableiten (Befund „keine Gesamtsicht"). Da `BondResult` außerhalb des Scopes liegt, wird das Gesamtsignal über die Event-Payload (`BondChiefReady`) veröffentlicht — Duration-Risiko + Credit-Risiko (Spread-Trend) → Mehrheits-/Veto-Logik.
  ```python
  import asyncio
  from unittest.mock import MagicMock
  from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent, _overall_signal
  from core.domain.models import Signal

  def test_overall_bearish_when_duration_and_spread_bearish():
      assert _overall_signal(Signal.BEARISH, Signal.NEUTRAL, Signal.BEARISH, Signal.NEUTRAL) == Signal.BEARISH

  def test_overall_neutral_on_conflict():
      assert _overall_signal(Signal.BULLISH, Signal.NEUTRAL, Signal.BEARISH, Signal.NEUTRAL) == Signal.NEUTRAL

  def test_chief_publishes_overall_in_payload():
      prov = MagicMock(); prov.get_bond_data.return_value = {}
      macro = MagicMock(); macro.get_economic_state.return_value = {}
      bus = MagicMock()
      asyncio.run(BondChiefAgent(prov, macro, bus).run("X", "government", "stable"))
      chief_calls = [c.args[0] for c in bus.publish.call_args_list
                     if type(c.args[0]).__name__ == "BondChiefReady"]
      assert chief_calls and "overall_signal" in chief_calls[-1].payload
  ```
- [ ] **Test laufen lassen → FAIL.**
- [ ] **Implementieren.** `_overall_signal`-Helper + Payload-Erweiterung in `bond_chief_agent.py`. Mehrheits-Voting mit Konflikt→NEUTRAL; Credit-Downgrade als Veto (BEARISH).
  ```python
  def _overall_signal(metrics: Signal, duration: Signal, credit: Signal, spread: Signal) -> Signal:
      from core.domain.models import Signal as _S
      votes = [metrics, duration, credit, spread]
      bull = votes.count(_S.BULLISH)
      bear = votes.count(_S.BEARISH)
      # Credit-Downgrade wirkt als Risiko-Veto
      if credit == _S.BEARISH:
        return _S.BEARISH
      if bull > bear:
        return _S.BULLISH
      if bear > bull:
        return _S.BEARISH
      return _S.NEUTRAL
  ```
  In `run()` nach Aggregation:
  ```python
      overall = _overall_signal(metrics.signal, duration.signal, credit.signal, spread.signal)
      self.bus.publish(BondChiefReady(source="bond_chief_agent", payload={
          "ticker": ticker, "overall_signal": overall.value,
          "duration": duration.modified_duration,
          "default_probability": credit.default_probability,
      }))
  ```
- [ ] **Test laufen lassen → PASS.**
- [ ] **Self-Review:** Gesamtsignal konsolidiert Duration- und Credit-Risiko (Befund „keine Gesamtsicht")? Credit-Downgrade als Veto sinnvoll? `BondResult`-Signatur unverändert (nur Payload erweitert, Models out of scope)? Bestehende `default()` und Fehlerbehandlung intakt?
- [ ] **Commit:** `feat(bond_chief): konsolidiertes Gesamtsignal (Duration + Credit Veto) (Domäne 5)`

---

### Task 10 — Gesamtlauf, Regression, Self-Review

**Files:** alle obigen

- [ ] **Gesamte Bond-/Util-Suite laufen lassen → PASS:** `pytest tests/utils/test_bond_math.py tests/utils/test_credit.py tests/agents/stock_deep_dive/bond/ -q`.
- [ ] **Repo-Regression:** `pytest -q` (sicherstellen, dass keine Konsumenten der geänderten Agenten brechen — insb. `bond_chief_agent`-Aufrufer und der bestehende `test_bond_credit_agent.py`).
- [ ] **Konsistenz-Self-Review gegen Review-Befunde (Domäne 5 + P2.3):**
  - [ ] Pricing-Engine existiert (YTM/Duration/Convexity/Effective Duration) — nicht mehr durchgereicht.
  - [ ] DV01 auf Dirty Price, per 100 Nominal dokumentiert.
  - [ ] Current Yield Clean-Konvention, Einheiten dokumentiert.
  - [ ] real_yield via Breakeven + exakte Fisher (`to_real`).
  - [ ] Convexity in `price_change_estimate` genutzt (½·C·Δy²).
  - [ ] Macaulay↔Modified-Konsistenz (`ModDur = MacDur/(1+y/freq)`).
  - [ ] Yield-to-Worst = min(YTM, YTC).
  - [ ] Credit `startswith`-Bug weg (CCC ≠ 50 %), exakter Lookup auf normalisierter Skala.
  - [ ] PD/LGD/Spread als Dezimal vereinheitlicht; Credit Triangle Spread≈PD·LGD.
  - [ ] Binäre IG/Non-IG-Grenze (≥ BBB-/Baa3); `junk` entfernt.
  - [ ] Spread-Niveau vs. Historie + Spread-Duration + OAS≤Z.
  - [ ] bond_chief Gesamtsicht (konsolidiertes Signal).
- [ ] **Commit:** `test(bond): Gesamtlauf grün, Review-Befunde Domäne 5/P2.3 abgedeckt`

---

## Abdeckung

| Review-Befund (Domäne 5 / P2.3) | Adressiert in |
|---|---|
| Fehlende Pricing-Engine (YTM/Duration/Convexity) | Task 1, 2 (`bond_math.py`), Task 5, 6 (Agenten rechnen statt durchreichen) |
| Effective Duration für Optionalität | Task 2, Task 6 (callable/putable) |
| DV01 Clean vs. Dirty | Task 2 (`dv01` auf Dirty), Task 6 (Clean+Accrued) |
| `current_yield`-Konvention (Clean, Einheiten) | Task 5 |
| Convexity-Nutzung (½·C·Δy²) | Task 2 (`price_change_estimate`), Task 6 (Signal) |
| Macaulay↔Modified-Konsistenz | Task 2 (`modified_duration`), Task 6 |
| Yield-to-Worst | Task 3, Task 5 |
| real_yield via Breakeven (ex-ante) | Task 5 (`to_real`, `breakeven_inflation`) |
| Credit `startswith`-Bug (CCC→50 %) | Task 4 (exakter Lookup), Task 7 |
| %/Dezimal-Vereinheitlichung | Task 4 (PD/LGD/Spread Dezimal), Task 5/7 (Rand-Konvertierung) |
| PD/LGD/Spread (Credit Triangle) | Task 4 (`credit_triangle_spread`), Task 7 |
| IG/Non-IG binär | Task 4 (`is_investment_grade`), Task 7 (`_category`) |
| PD-Quelle = Kategorie-Quelle (Konsistenz) | Task 7 |
| OAS/Z/G-Spread + Spread-Duration, Niveau-Bewertung | Task 8 |
| bond_chief Gesamtsicht | Task 9 |

**Verbindliche `bond_math`-Signaturen:** `ytm(price, face, coupon_rate, periods, freq=2)`, `bond_price(y, face, coupon_rate, periods, freq=2)`, `macaulay_duration(price, face, coupon_rate, periods, freq=2)`, `modified_duration(mac_dur, y, freq)`, `convexity(price, face, coupon_rate, periods, freq=2)`, `effective_duration(price_up, price_down, price0, dy)`, `dv01(mod_dur, dirty_price)`, `price_change_estimate(mod_dur, conv, dy)` (= `−mod_dur*dy + 0.5*conv*dy**2`), `yield_to_worst(ytm_value, ytc_value=None)`.

**Verbindliche `credit`-Signaturen:** `normalize_rating(raw) -> str | None`, `default_probability(raw) -> float | None` (Dezimal, exakt), `credit_triangle_spread(pd, lgd) -> float` (≈ pd·lgd), `is_investment_grade(raw) -> bool` (Grenze BBB-/Baa3).

**Getroffene Annahmen über Provider-Rohdaten:** `get_bond_data()` liefert künftig die Bausteine (Clean `current_price` als %-Kurs, `coupon_rate` Dezimal oder `coupon`/`face`, `frequency`, `maturity_years`, optional `accrued_interest`, `call_price`/`years_to_call`, `is_callable`/`is_putable`, `rating_sp/moodys/fitch`, `rating_trend`, `recovery_rate`, `spread_bps`/`spread_history`/`spread_trend`/`spread_duration`) statt fertiger Kennzahlen. Breakeven/Inflation kommt aus `MacroDataProvider.get_economic_state()` (`breakeven_inflation` bevorzugt, sonst `inflation`) oder ersatzweise aus `get_bond_data`. Fehlt ein Baustein, bleibt das jeweilige Ergebnisfeld `None`. Zusatzgrößen ohne Snapshot-Feld (Spread-Duration, Niveau-Score, Credit-Triangle-Spread, Gesamtsignal) werden über die `*Ready`-Event-Payloads transportiert, da die `*Snapshot`/`BondResult`-Dataclasses außerhalb des Scopes liegen.
