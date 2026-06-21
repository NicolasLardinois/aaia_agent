# Bond-Risikoaffinität & Credit-Band-Aggregation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Das Bond-Gesamtsignal aus einem starren Credit-Veto in eine risiko-affinitäts-gewichtete Aggregation überführen und die Risikoaffinität pro Anleihe als Pflicht-Eingabe erfassen, persistieren, anzeigen und nachträglich neu berechenbar machen.

**Architecture:** Reine Logik in `core/utils/bond_risk.py` (S&P-Rating → 3 Bänder → Beitrag × Affinität → gleich-gewichtete Aggregation). Der `bond_chief` nutzt sie und schreibt das Gesamtsignal ins `BondResult`. Die Affinität wird vom CLI durch Orchestrator → Chief gereicht, je Position persistiert (Portfolio + Analyse-Memory) und über die gespeicherten Bausteine billig neu berechenbar.

**Tech Stack:** Python 3.12, dataclasses, pytest. Keine neuen Libs.

Spec: `docs/superpowers/specs/2026-06-21-bond-risikoaffinitaet-design.md`

## Global Constraints

- Type Hints moderne Syntax (`X | None`, `dict[str, float]`). Kommentare auf **Deutsch**.
- **TDD Pflicht:** erst roter Test, dann minimal grün. `python -m pytest -q`.
- **Hexagonal:** `core/` und `agents/` importieren **nie** aus `adapters/`. Reine Logik seiteneffektfrei.
- **Git:** je Task eigener Commit mit **expliziten Pfaden** — **kein `git add -A`** (im Working Tree liegt fremde, untrackte Arbeit).
- Aggregations-Schwelle: `net > +0.15 → BULLISH`, `net < -0.15 → BEARISH`, sonst `NEUTRAL`; `confidence = min(1.0, abs(net))`.
- Enum-Werte deutsch: `RiskAffinity` = `konservativ|neutral|risikofreudig`; `CreditBand` = `sicher|mittel|riskant`.

---

### Task 1: Domänen-Enums `RiskAffinity` + `CreditBand`

**Files:**
- Modify: `core/domain/models.py` (bei den übrigen Enums, nach `class Signal`)
- Test: `tests/domain/test_risk_enums.py`

**Interfaces:**
- Produces: `RiskAffinity(str, Enum)` mit `KONSERVATIV/NEUTRAL/RISIKOFREUDIG`; `CreditBand(str, Enum)` mit `SICHER/MITTEL/RISKANT`.

- [ ] **Step 1: Failing test**

```python
# tests/domain/test_risk_enums.py
from core.domain.models import RiskAffinity, CreditBand


def test_risk_affinity_values():
    assert RiskAffinity.KONSERVATIV.value == "konservativ"
    assert RiskAffinity.NEUTRAL.value == "neutral"
    assert RiskAffinity.RISIKOFREUDIG.value == "risikofreudig"
    assert RiskAffinity("neutral") == RiskAffinity.NEUTRAL


def test_credit_band_values():
    assert CreditBand.SICHER.value == "sicher"
    assert CreditBand.MITTEL.value == "mittel"
    assert CreditBand.RISKANT.value == "riskant"
```

- [ ] **Step 2: Run → fail**

Run: `python -m pytest tests/domain/test_risk_enums.py -q`
Expected: FAIL (`ImportError: cannot import name 'RiskAffinity'`).

- [ ] **Step 3: Implement** — in `core/domain/models.py` direkt nach `class Signal(str, Enum): …` einfügen:

```python
class RiskAffinity(str, Enum):
    KONSERVATIV   = "konservativ"
    NEUTRAL       = "neutral"
    RISIKOFREUDIG = "risikofreudig"


class CreditBand(str, Enum):
    SICHER  = "sicher"
    MITTEL  = "mittel"
    RISKANT = "riskant"
```

- [ ] **Step 4: Run → pass**

Run: `python -m pytest tests/domain/test_risk_enums.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add core/domain/models.py tests/domain/test_risk_enums.py
git commit -m "feat(domain): RiskAffinity- und CreditBand-Enums (Bond-Risikoaffinität)"
```

---

### Task 2: Reine Logik `core/utils/bond_risk.py`

**Files:**
- Create: `core/utils/bond_risk.py`
- Test: `tests/utils/test_bond_risk.py`

**Interfaces:**
- Consumes: `RiskAffinity`, `CreditBand`, `Signal` (Task 1 / models).
- Produces:
  - `rating_to_band(rating: str | None) -> CreditBand | None`
  - `credit_contribution(band: CreditBand, affinity: RiskAffinity) -> float`
  - `aggregate_bond_signal(metrics: Signal | None, duration: Signal | None, spread: Signal | None, credit_band: CreditBand | None, affinity: RiskAffinity) -> tuple[Signal, float]`

- [ ] **Step 1: Failing test (rating_to_band)**

```python
# tests/utils/test_bond_risk.py
from core.domain.models import Signal, RiskAffinity, CreditBand
from core.utils.bond_risk import rating_to_band, credit_contribution, aggregate_bond_signal


def test_rating_to_band_grenzen():
    assert rating_to_band("AAA")  == CreditBand.SICHER
    assert rating_to_band("BBB-") == CreditBand.SICHER     # untere IG-Kante
    assert rating_to_band("BB+")  == CreditBand.MITTEL      # obere HY-Kante
    assert rating_to_band("B-")   == CreditBand.MITTEL
    assert rating_to_band("CCC+") == CreditBand.RISKANT     # Distressed-Beginn
    assert rating_to_band("D")    == CreditBand.RISKANT
    assert rating_to_band("bbb-") == CreditBand.SICHER      # case-insensitiv
    assert rating_to_band(None)   is None
    assert rating_to_band("NR")   is None                   # unbekannt
```

- [ ] **Step 2: Run → fail** (`ModuleNotFoundError: core.utils.bond_risk`).

- [ ] **Step 3: Implement (rating_to_band)** — `core/utils/bond_risk.py`:

```python
from core.domain.models import Signal, RiskAffinity, CreditBand

_SICHER  = {"AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"}
_MITTEL  = {"BB+", "BB", "BB-", "B+", "B", "B-"}
_RISKANT = {"CCC+", "CCC", "CCC-", "CC", "C", "D"}


def rating_to_band(rating: str | None) -> CreditBand | None:
    """S&P-Langfristrating → Credit-Band. Unbekannt/fehlend → None (Credit unverfügbar)."""
    if rating is None:
        return None
    r = rating.strip().upper()
    if r in _SICHER:
        return CreditBand.SICHER
    if r in _MITTEL:
        return CreditBand.MITTEL
    if r in _RISKANT:
        return CreditBand.RISKANT
    return None
```

- [ ] **Step 4: Run → pass**.

- [ ] **Step 5: Failing test (credit_contribution)** — anhängen:

```python
def test_credit_contribution_tabelle():
    K, N, R = RiskAffinity.KONSERVATIV, RiskAffinity.NEUTRAL, RiskAffinity.RISIKOFREUDIG
    assert credit_contribution(CreditBand.SICHER, K) == 0.0
    assert credit_contribution(CreditBand.SICHER, R) == 0.0
    assert credit_contribution(CreditBand.MITTEL, K) == -1.0
    assert credit_contribution(CreditBand.MITTEL, N) == -0.5
    assert credit_contribution(CreditBand.MITTEL, R) == 0.0
    assert credit_contribution(CreditBand.RISKANT, K) == -1.5
    assert credit_contribution(CreditBand.RISKANT, N) == -1.0
    assert credit_contribution(CreditBand.RISKANT, R) == -0.5
```

- [ ] **Step 6: Run → fail**.

- [ ] **Step 7: Implement (credit_contribution)** — anhängen:

```python
_CONTRIB: dict[CreditBand, dict[RiskAffinity, float]] = {
    CreditBand.SICHER:  {RiskAffinity.KONSERVATIV: 0.0, RiskAffinity.NEUTRAL: 0.0,  RiskAffinity.RISIKOFREUDIG: 0.0},
    CreditBand.MITTEL:  {RiskAffinity.KONSERVATIV: -1.0, RiskAffinity.NEUTRAL: -0.5, RiskAffinity.RISIKOFREUDIG: 0.0},
    CreditBand.RISKANT: {RiskAffinity.KONSERVATIV: -1.5, RiskAffinity.NEUTRAL: -1.0, RiskAffinity.RISIKOFREUDIG: -0.5},
}


def credit_contribution(band: CreditBand, affinity: RiskAffinity) -> float:
    """Numerischer Credit-Beitrag = f(Band, Risikoaffinität). Nie positiv: Ausfallrisiko
    ist kein Pluspunkt — die Rendite belohnt separat über das metrics-Signal."""
    return _CONTRIB[band][affinity]
```

- [ ] **Step 8: Run → pass**.

- [ ] **Step 9: Failing test (aggregate_bond_signal)** — anhängen. Deckt die Spec-Beispiele, Schwellen und Unverfügbarkeit:

```python
def test_aggregate_bb_bond_skaliert_mit_affinitaet():
    # BB (Mittel), Rendite attraktiv: metrics +1, duration 0, spread 0
    base = (Signal.BULLISH, Signal.NEUTRAL, Signal.NEUTRAL, CreditBand.MITTEL)
    assert aggregate_bond_signal(*base, RiskAffinity.KONSERVATIV)[0]   == Signal.NEUTRAL
    assert aggregate_bond_signal(*base, RiskAffinity.NEUTRAL)[0]       == Signal.NEUTRAL
    assert aggregate_bond_signal(*base, RiskAffinity.RISIKOFREUDIG)[0] == Signal.BULLISH


def test_aggregate_ccc_bond_bleibt_riskant():
    # CCC (Riskant), Stress: metrics +1, duration 0, spread -1
    base = (Signal.BULLISH, Signal.NEUTRAL, Signal.BEARISH, CreditBand.RISKANT)
    assert aggregate_bond_signal(*base, RiskAffinity.KONSERVATIV)[0]   == Signal.BEARISH
    assert aggregate_bond_signal(*base, RiskAffinity.NEUTRAL)[0]       == Signal.BEARISH
    assert aggregate_bond_signal(*base, RiskAffinity.RISIKOFREUDIG)[0] == Signal.NEUTRAL


def test_aggregate_unverfuegbares_credit_renormalisiert():
    # Kein Rating → credit_band None → nur metrics/duration/spread zählen.
    sig, conf = aggregate_bond_signal(Signal.BULLISH, Signal.BULLISH, Signal.NEUTRAL, None, RiskAffinity.NEUTRAL)
    assert sig == Signal.BULLISH            # (1+1+0)/3 = 0.667 > 0.15
    assert 0.0 < conf <= 1.0


def test_aggregate_alles_unverfuegbar_ist_neutral():
    assert aggregate_bond_signal(None, None, None, None, RiskAffinity.NEUTRAL) == (Signal.NEUTRAL, 0.0)
```

- [ ] **Step 10: Run → fail**.

- [ ] **Step 11: Implement (aggregate_bond_signal)** — anhängen:

```python
_SCORE = {Signal.BULLISH: 1.0, Signal.NEUTRAL: 0.0, Signal.BEARISH: -1.0}
_THRESHOLD = 0.15


def aggregate_bond_signal(
    metrics: Signal | None,
    duration: Signal | None,
    spread: Signal | None,
    credit_band: CreditBand | None,
    affinity: RiskAffinity,
) -> tuple[Signal, float]:
    """Gleich gewichteter Mittelwert der verfügbaren Komponenten (kein Veto).
    metrics/duration/spread → ±1/0; credit → Beitrag (Band × Affinität, bis -1.5).
    Unverfügbare Komponente (None) wird weggelassen → restliche re-normalisiert."""
    parts: list[float] = []
    for sig in (metrics, duration, spread):
        if sig is not None:
            parts.append(_SCORE[sig])
    if credit_band is not None:
        parts.append(credit_contribution(credit_band, affinity))
    if not parts:
        return Signal.NEUTRAL, 0.0
    net = sum(parts) / len(parts)
    confidence = min(1.0, abs(net))
    if net > _THRESHOLD:
        return Signal.BULLISH, confidence
    if net < -_THRESHOLD:
        return Signal.BEARISH, confidence
    return Signal.NEUTRAL, confidence
```

- [ ] **Step 12: Run → pass** (alle `tests/utils/test_bond_risk.py`).

- [ ] **Step 13: Commit**

```bash
git add core/utils/bond_risk.py tests/utils/test_bond_risk.py
git commit -m "feat(bond): reine Credit-Band-/Risikoaffinitäts-Aggregation (bond_risk)"
```

---

### Task 3: `BondResult` um Gesamtsignal + Affinität erweitern

**Files:**
- Modify: `core/domain/models.py` (`@dataclass class BondResult`, aktuell Felder ticker/bond_type/metrics/duration/credit/spread)
- Test: `tests/domain/test_bond_result_fields.py`

**Interfaces:**
- Produces: `BondResult` mit Zusatzfeldern `overall_signal: Signal = Signal.NEUTRAL`, `confidence: float = 0.0`, `risk_affinity: RiskAffinity | None = None`, `credit_band: CreditBand | None = None`.

- [ ] **Step 1: Failing test**

```python
# tests/domain/test_bond_result_fields.py
from core.domain.models import (
    BondResult, BondMetricsSnapshot, BondDurationSnapshot, BondCreditSnapshot,
    BondSpreadSnapshot, Signal, RiskAffinity, CreditBand,
)


def _snap():
    m = BondMetricsSnapshot(bond_type="corporate", current_price=None, coupon=None,
        maturity_years=None, ytm=None, ytc=None, current_yield=None, real_yield=None,
        country=None, breakeven_inflation=None, issuer=None, sector=None, signal=Signal.BULLISH)
    d = BondDurationSnapshot(macaulay_duration=None, modified_duration=None, convexity=None, dv01=None, signal=Signal.NEUTRAL)
    c = BondCreditSnapshot(moodys=None, sp="BB", fitch=None, category="high_yield", trend="stable", default_probability=None, signal=Signal.NEUTRAL)
    s = BondSpreadSnapshot(spread_bps=None, oas=None, z_spread=None, spread_trend="stable", signal=Signal.NEUTRAL)
    return m, d, c, s


def test_bond_result_has_overall_and_affinity_defaults():
    m, d, c, s = _snap()
    r = BondResult(ticker="X", bond_type="corporate", metrics=m, duration=d, credit=c, spread=s)
    assert r.overall_signal == Signal.NEUTRAL
    assert r.confidence == 0.0
    assert r.risk_affinity is None
    assert r.credit_band is None


def test_bond_result_accepts_overall_and_affinity():
    m, d, c, s = _snap()
    r = BondResult(ticker="X", bond_type="corporate", metrics=m, duration=d, credit=c, spread=s,
                   overall_signal=Signal.BULLISH, confidence=0.25,
                   risk_affinity=RiskAffinity.RISIKOFREUDIG, credit_band=CreditBand.MITTEL)
    assert r.overall_signal == Signal.BULLISH
    assert r.risk_affinity == RiskAffinity.RISIKOFREUDIG
    assert r.credit_band == CreditBand.MITTEL
```

- [ ] **Step 2: Run → fail** (`TypeError: unexpected keyword argument 'overall_signal'`).

- [ ] **Step 3: Implement** — in `core/domain/models.py` `BondResult` ergänzen (Felder MIT Defaults ans Ende, rückwärtskompatibel):

```python
@dataclass
class BondResult:
    ticker: str
    bond_type: str
    metrics: BondMetricsSnapshot
    duration: BondDurationSnapshot
    credit: BondCreditSnapshot
    spread: BondSpreadSnapshot
    overall_signal: Signal = Signal.NEUTRAL
    confidence: float = 0.0
    risk_affinity: "RiskAffinity | None" = None
    credit_band: "CreditBand | None" = None
```

- [ ] **Step 4: Run → pass**.

- [ ] **Step 5: Commit**

```bash
git add core/domain/models.py tests/domain/test_bond_result_fields.py
git commit -m "feat(domain): BondResult um overall_signal/confidence/risk_affinity/credit_band"
```

---

### Task 4: `bond_chief_agent` auf Aggregation umstellen

**Files:**
- Modify: `agents/stock_deep_dive/bond_chief_agent.py` (entferne `_overall_signal`-Veto; `run` bekommt `risk_affinity`)
- Test: `tests/agents/stock_deep_dive/test_bond_chief_agent.py` (ergänzen)

**Interfaces:**
- Consumes: `aggregate_bond_signal`, `rating_to_band` (Task 2); `BondResult` (Task 3); `credit.sp` aus `BondCreditSnapshot`.
- Produces: `BondChiefAgent.run(ticker, bond_type, rate_direction, risk_affinity) -> BondResult` mit befülltem `overall_signal/confidence/risk_affinity/credit_band`.

- [ ] **Step 1: Failing test** — die Sub-Agenten mocken, Affinität variieren:

```python
# in tests/agents/stock_deep_dive/test_bond_chief_agent.py ergänzen
import asyncio
from unittest.mock import AsyncMock, MagicMock
from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent
from core.domain.models import (
    Signal, RiskAffinity, CreditBand,
    BondMetricsSnapshot, BondDurationSnapshot, BondCreditSnapshot, BondSpreadSnapshot,
)


def _bb_chief():
    chief = BondChiefAgent(MagicMock(), MagicMock(), MagicMock())
    m = BondMetricsSnapshot(bond_type="corporate", current_price=None, coupon=None,
        maturity_years=None, ytm=None, ytc=None, current_yield=None, real_yield=None,
        country=None, breakeven_inflation=None, issuer=None, sector=None, signal=Signal.BULLISH)
    d = BondDurationSnapshot(macaulay_duration=None, modified_duration=None, convexity=None, dv01=None, signal=Signal.NEUTRAL)
    c = BondCreditSnapshot(moodys=None, sp="BB", fitch=None, category="high_yield", trend="stable", default_probability=None, signal=Signal.NEUTRAL)
    s = BondSpreadSnapshot(spread_bps=None, oas=None, z_spread=None, spread_trend="stable", signal=Signal.NEUTRAL)
    chief.bond_metrics_agent.run  = AsyncMock(return_value=m)
    chief.bond_duration_agent.run = AsyncMock(return_value=d)
    chief.bond_credit_agent.run   = AsyncMock(return_value=c)
    chief.bond_spread_agent.run   = AsyncMock(return_value=s)
    return chief


def test_bond_chief_risikofreudig_macht_bb_bullish():
    chief = _bb_chief()
    res = asyncio.run(chief.run("X", "corporate", "stable", RiskAffinity.RISIKOFREUDIG))
    assert res.overall_signal == Signal.BULLISH
    assert res.risk_affinity == RiskAffinity.RISIKOFREUDIG
    assert res.credit_band == CreditBand.MITTEL


def test_bond_chief_konservativ_macht_bb_neutral():
    chief = _bb_chief()
    res = asyncio.run(chief.run("X", "corporate", "stable", RiskAffinity.KONSERVATIV))
    assert res.overall_signal == Signal.NEUTRAL
```

- [ ] **Step 2: Run → fail** (`run()` nimmt noch kein `risk_affinity` / `overall_signal` fehlt).

- [ ] **Step 3: Implement** — `bond_chief_agent.py`: `_overall_signal` löschen; oben ergänzen
`from core.domain.models import BondResult, Signal, RiskAffinity, CreditBand`
`from core.utils.bond_risk import rating_to_band, aggregate_bond_signal`; `run` ersetzen:

```python
    async def run(self, ticker: str, bond_type: str, rate_direction: str,
                  risk_affinity: RiskAffinity) -> BondResult:
        results = await asyncio.gather(
            self.bond_metrics_agent.run(ticker, bond_type),
            self.bond_duration_agent.run(ticker, rate_direction),
            self.bond_credit_agent.run(ticker),
            self.bond_spread_agent.run(ticker),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        metrics  = _safe(results[0], BondMetricsAgent.default())
        duration = _safe(results[1], BondDurationAgent.default())
        credit   = _safe(results[2], BondCreditAgent.default())
        spread   = _safe(results[3], BondSpreadAgent.default())

        credit_band = rating_to_band(credit.sp)
        overall, confidence = aggregate_bond_signal(
            metrics.signal, duration.signal, spread.signal, credit_band, risk_affinity,
        )
        self.bus.publish(BondChiefReady(source="bond_chief_agent", payload={
            "ticker": ticker, "overall_signal": overall.value,
            "duration": duration.modified_duration,
            "default_probability": credit.default_probability,
        }))
        return BondResult(
            ticker=ticker, bond_type=bond_type,
            metrics=metrics, duration=duration, credit=credit, spread=spread,
            overall_signal=overall, confidence=confidence,
            risk_affinity=risk_affinity, credit_band=credit_band,
        )
```

- [ ] **Step 4: Run → pass** (neue Tests + vorhandene `test_bond_chief_agent.py`; ggf. alte Veto-Tests entfernen/anpassen, die `_overall_signal` direkt prüften).

- [ ] **Step 5: Commit**

```bash
git add agents/stock_deep_dive/bond_chief_agent.py tests/agents/stock_deep_dive/test_bond_chief_agent.py
git commit -m "feat(bond): bond_chief aggregiert via Risikoaffinität statt Credit-Veto (#47)"
```

---

### Task 5: `risk_affinity` durchreichen (Orchestrator → main → CLI)

**Files:**
- Modify: `orchestrators/bottom_up_orchestrator.py` (`run`, `_run_bond`)
- Modify: `app/main.py` (`run_bottom_up`, `main`-Parsing)
- Test: `tests/test_cli_risk_affinity.py`

**Interfaces:**
- Consumes: `BondChiefAgent.run(..., risk_affinity)` (Task 4), `RiskAffinity` (Task 1).
- Produces: CLI verlangt `--risk-affinity {konservativ|neutral|risikofreudig}` bei `asset_class=="bond"`; fehlt/ungültig → Exit 1.

- [ ] **Step 1: Failing test**

```python
# tests/test_cli_risk_affinity.py
import pytest
from app.main import _parse_risk_affinity
from core.domain.models import RiskAffinity


def test_bond_ohne_affinitaet_bricht_ab():
    with pytest.raises(SystemExit):
        _parse_risk_affinity([], "bond")


def test_bond_ungueltige_affinitaet_bricht_ab():
    with pytest.raises(SystemExit):
        _parse_risk_affinity(["--risk-affinity", "yolo"], "bond")


def test_bond_gueltige_affinitaet():
    assert _parse_risk_affinity(["--risk-affinity", "neutral"], "bond") == RiskAffinity.NEUTRAL


def test_nicht_bond_braucht_keine_affinitaet():
    assert _parse_risk_affinity([], "equity") is None
```

- [ ] **Step 2: Run → fail** (`ImportError: _parse_risk_affinity`).

- [ ] **Step 3: Implement (app/main.py)** — Helfer + `run_bottom_up`-Signatur + Aufruf + Dispatch:

```python
# oben bei den Imports:
from core.domain.models import RiskAffinity

def _parse_risk_affinity(args: list[str], asset_class: str) -> "RiskAffinity | None":
    val = None
    if "--risk-affinity" in args:
        i = args.index("--risk-affinity")
        if i + 1 < len(args):
            val = args[i + 1]
    if asset_class != "bond":
        return None
    if val is None:
        print("Fehler: Anleihe-Analyse erfordert --risk-affinity {konservativ|neutral|risikofreudig}")
        sys.exit(1)
    try:
        return RiskAffinity(val)
    except ValueError:
        print(f"Fehler: ungültige --risk-affinity {val!r}. Erlaubt: konservativ|neutral|risikofreudig")
        sys.exit(1)
```

`run_bottom_up` um `risk_affinity: "RiskAffinity | None" = None` erweitern und an `orch.run(...)` durchreichen:

```python
async def run_bottom_up(ticker, asset_class="equity", sector="default",
                        bond_type="government", rate_direction="stable",
                        risk_affinity=None) -> None:
    ...
    result = await orch.run(
        ticker.upper(), asset_class=asset_class, sector=sector,
        bond_type=bond_type, rate_direction=rate_direction,
        risk_affinity=risk_affinity,
    )
```

Im `main()`-`bottomup`-Zweig die Flag-Token vor dem Positions-Parsing entfernen und Affinität bestimmen:

```python
    elif args[0] == "bottomup" and len(args) >= 2:
        # --risk-affinity <wert> herausziehen, damit es das Positions-Parsing nicht stört
        pos = list(args)
        if "--risk-affinity" in pos:
            i = pos.index("--risk-affinity")
            del pos[i:i + 2]
        asset_class    = pos[2] if len(pos) >= 3 else "equity"
        sector         = pos[3] if len(pos) >= 4 else "default"
        bond_type      = pos[4] if len(pos) >= 5 else "government"
        rate_direction = pos[5] if len(pos) >= 6 else "stable"
        risk_affinity  = _parse_risk_affinity(args, asset_class)
        asyncio.run(run_bottom_up(pos[1], asset_class=asset_class, sector=sector,
                                  bond_type=bond_type, rate_direction=rate_direction,
                                  risk_affinity=risk_affinity))
```

- [ ] **Step 4: Implement (orchestrator)** — `bottom_up_orchestrator.py`:
`run(...)` um `risk_affinity: "RiskAffinity | None" = None` erweitern und an `_run_bond` geben; `_run_bond` um den Parameter erweitern und an den Chief reichen:

```python
    async def _run_bond(self, ticker, bond_type, rate_direction, risk_affinity) -> BottomUpResult:
        try:
            bond_result = await self.bond_chief.run(ticker, bond_type, rate_direction, risk_affinity)
        except Exception:
            bond_result = BondChiefAgent.default(ticker, bond_type)
        return BottomUpResult(
            ticker=ticker, asset_class="bond",
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=bond_result, index=None, commodity_deep=None,
        )
```
(im Dispatch `return await self._run_bond(ticker, bond_type, rate_direction, risk_affinity)`).

- [ ] **Step 5: Run → pass** (`python -m pytest tests/test_cli_risk_affinity.py -q` + Gesamtsuite).

- [ ] **Step 6: Commit**

```bash
git add app/main.py orchestrators/bottom_up_orchestrator.py tests/test_cli_risk_affinity.py
git commit -m "feat(cli): --risk-affinity als Pflicht-Eingabe für Anleihe-Analysen"
```

---

### Task 6: `Position` + Portfolio-Provider um `risk_affinity`

**Files:**
- Modify: `core/domain/portfolio.py` (`Position`)
- Modify: `adapters/persistence/json_portfolio.py` (`get_positions`)
- Test: `tests/adapters/test_json_portfolio_risk_affinity.py`

**Interfaces:**
- Produces: `Position.risk_affinity: str | None = None`; Bond-Positionen ohne gültige Affinität → `PortfolioError`.

- [ ] **Step 1: Failing test**

```python
# tests/adapters/test_json_portfolio_risk_affinity.py
import json
import pytest
from adapters.persistence.json_portfolio import JsonPortfolioProvider
from core.domain.portfolio import PortfolioError


def _write(tmp_path, positions):
    p = tmp_path / "portfolio.json"
    p.write_text(json.dumps({"positions": positions}), encoding="utf-8")
    return str(p)


def test_bond_position_traegt_risk_affinity(tmp_path):
    path = _write(tmp_path, [{"ticker": "TLT", "shares": 10, "buy_price": 90,
        "direction": "long", "asset_class": "bond", "risk_affinity": "neutral"}])
    pos = JsonPortfolioProvider(path).get_positions()[0]
    assert pos.risk_affinity == "neutral"


def test_bond_ohne_risk_affinity_failt(tmp_path):
    path = _write(tmp_path, [{"ticker": "TLT", "shares": 10, "buy_price": 90,
        "direction": "long", "asset_class": "bond"}])
    with pytest.raises(PortfolioError):
        JsonPortfolioProvider(path).get_positions()


def test_equity_ohne_risk_affinity_ok(tmp_path):
    path = _write(tmp_path, [{"ticker": "AAPL", "shares": 10, "buy_price": 90,
        "direction": "long", "asset_class": "equity"}])
    assert JsonPortfolioProvider(path).get_positions()[0].risk_affinity is None
```

- [ ] **Step 2: Run → fail**.

- [ ] **Step 3: Implement (Position)** — `core/domain/portfolio.py`, Feld ans Ende (Defaults erlaubt, frozen):

```python
    country: str = "Unbekannt"
    risk_affinity: Optional[str] = None   # nur Anleihen; "konservativ"|"neutral"|"risikofreudig"
```

- [ ] **Step 4: Implement (Provider)** — in `json_portfolio.py` `get_positions`, vor dem `out.append(...)` ergänzen und Feld übergeben:

```python
            risk_affinity = d.get("risk_affinity")
            if d.get("asset_class", "equity") == "bond":
                if risk_affinity not in {"konservativ", "neutral", "risikofreudig"}:
                    raise PortfolioError(
                        f"Position {ticker}: Anleihe braucht 'risk_affinity' "
                        f"(konservativ|neutral|risikofreudig), war {risk_affinity!r}.")
            out.append(Position(
                ticker=ticker, shares=d["shares"], entry_price=d["buy_price"],
                direction=direction, currency=d.get("currency", "USD"),
                current_price=d.get("current_price"),
                sector=d.get("sector", "Unbekannt"),
                asset_class=d.get("asset_class", "equity"),
                country=d.get("country", "Unbekannt"),
                risk_affinity=risk_affinity))
```

- [ ] **Step 5: Run → pass**.

- [ ] **Step 6: Commit**

```bash
git add core/domain/portfolio.py adapters/persistence/json_portfolio.py tests/adapters/test_json_portfolio_risk_affinity.py
git commit -m "feat(portfolio): risk_affinity je Position (Pflicht für Anleihen)"
```

---

### Task 7: Portfolio-Monitor zeigt Risikoaffinität je Anleihe

**Files:**
- Modify: `agents/portfolio/portfolio_monitor_agent.py` (`_evaluate_positions` Snapshot + `run`-Ausgabe)
- Test: `tests/agents/portfolio/test_monitor_risk_affinity.py`

**Interfaces:**
- Consumes: `Position.risk_affinity` (Task 6).
- Produces: Snapshot-Feld `bond_risk_affinities: list[dict]` (`{"ticker","risk_affinity"}`) für Anleihe-Positionen.

- [ ] **Step 1: Failing test**

```python
# tests/agents/portfolio/test_monitor_risk_affinity.py
from unittest.mock import MagicMock
from agents.portfolio.portfolio_monitor_agent import PortfolioMonitorAgent
from core.domain.portfolio import Position


def _agent():
    return PortfolioMonitorAgent(memory=MagicMock(), portfolio_port=MagicMock())


def test_snapshot_listet_bond_affinitaeten():
    positions = [
        Position(ticker="TLT", shares=10, entry_price=90, direction="long",
                 asset_class="bond", risk_affinity="neutral"),
        Position(ticker="AAPL", shares=5, entry_price=100, direction="long",
                 asset_class="equity"),
    ]
    snap = _agent()._evaluate_positions(
        positions, market_data={0: {"price": 90, "beta": 1.0, "returns": None},
                                1: {"price": 100, "beta": 1.0, "returns": None}})
    assert {"ticker": "TLT", "risk_affinity": "neutral"} in snap["bond_risk_affinities"]
    assert all(e["ticker"] != "AAPL" for e in snap["bond_risk_affinities"])
```

- [ ] **Step 2: Run → fail** (`KeyError: 'bond_risk_affinities'`).

- [ ] **Step 3: Implement** — im `_evaluate_positions` vor dem `return {...}` berechnen und ins Dict (auch in den leeren Früh-Return mit `[]`):

```python
        bond_risk_affinities = [
            {"ticker": p.ticker, "risk_affinity": p.risk_affinity}
            for p in positions if p.asset_class == "bond" and p.risk_affinity is not None
        ]
```
Im Rückgabe-Dict ergänzen: `"bond_risk_affinities": bond_risk_affinities,` (und im leeren Snapshot `"bond_risk_affinities": [],`).
In `run()` nach den net-β-Zeilen ausgeben:

```python
        for e in snapshot.get("bond_risk_affinities", []):
            print(f"  Anleihe {e['ticker']}: Risikoaffinität = {e['risk_affinity']}")
```

- [ ] **Step 4: Run → pass**.

- [ ] **Step 5: Commit**

```bash
git add agents/portfolio/portfolio_monitor_agent.py tests/agents/portfolio/test_monitor_risk_affinity.py
git commit -m "feat(portfolio): Monitor zeigt Risikoaffinität je Anleihe-Position"
```

---

### Task 8: Analyse persistieren — `risk_affinity` + Recompute-Bausteine

**Files:**
- Modify: `adapters/memory/supabase_memory.py` (`save_analysis`, INSERT)
- Modify: `db/schema.sql` (Spalte nachziehen)
- Test: `tests/test_supabase_memory.py` (ergänzen — gemocktes `_connect`-Muster ist vorhanden)

**Interfaces:**
- Consumes: `result.bottom_up.bond` (BondResult mit `risk_affinity`, `credit_band`, Sub-Signalen).
- Produces: Spalte `analysis_memory.risk_affinity text`; im `indicators_snapshot`-JSON die Bausteine `bond_credit_band`, `bond_metrics_signal`, `bond_duration_signal`, `bond_spread_signal`.

- [ ] **Step 1: Failing test** — im vorhandenen `_save_and_capture`-Stil (siehe Datei):

```python
def test_save_analysis_persistiert_bond_risk_affinity(monkeypatch):
    from types import SimpleNamespace
    from core.domain.models import Signal, RiskAffinity, CreditBand
    bond = SimpleNamespace(
        valuation_range=None, index=None, precious_metals=None, commodity_deep=None,
        fundamentals=None, short_interest=None, insider=None,
        risk_affinity=RiskAffinity.NEUTRAL, credit_band=CreditBand.MITTEL,
        metrics=SimpleNamespace(signal=Signal.BULLISH),
        duration=SimpleNamespace(signal=Signal.NEUTRAL),
        spread=SimpleNamespace(signal=Signal.NEUTRAL),
    )
    params = _save_and_capture(_result_with_bu(bond), monkeypatch=monkeypatch)
    assert "neutral" in params           # risk_affinity-Spalte
    import json as _j
    snap = _j.loads(params[-1])
    assert snap.get("bond_credit_band") == "mittel"
    assert snap.get("bond_metrics_signal") == "bullish"
```

- [ ] **Step 2: Run → fail**.

- [ ] **Step 3: Implement** — in `save_analysis`, nach dem Bottom-Up-Indikatorblock, Bond-Bausteine defensiv einsammeln (nutzt den vorhandenen `_safe_value`/`_put`-Helfer aus Bug #46):

```python
        bond = getattr(bu, "bond", None) if bu else None
        risk_affinity_val = None
        if bond is not None:
            ra = getattr(bond, "risk_affinity", None)
            risk_affinity_val = ra.value if ra is not None else None
            cb = getattr(bond, "credit_band", None)
            if cb is not None:
                indicators["bond_credit_band"] = cb.value
            for feld, attr in (("bond_metrics_signal", "metrics"),
                               ("bond_duration_signal", "duration"),
                               ("bond_spread_signal", "spread")):
                _put(indicators, feld, lambda a=attr: getattr(bond, a).signal.value)
```
Im INSERT die Spalte `risk_affinity` aufnehmen (Spaltenliste + `%s` + Param `risk_affinity_val`), analog zu `short_action`.

- [ ] **Step 4: Implement (schema)** — `db/schema.sql`: `analysis_memory` um `risk_affinity text` ergänzen + Migrationsnotiz am Dateiende: `ALTER TABLE analysis_memory ADD COLUMN risk_affinity text;`

- [ ] **Step 5: Run → pass**.

- [ ] **Step 6: Commit**

```bash
git add adapters/memory/supabase_memory.py db/schema.sql tests/test_supabase_memory.py
git commit -m "feat(memory): risk_affinity + Bond-Recompute-Bausteine persistieren"
```

> **⚠️ Deploy:** vor Merge einmalig auf Supabase `ALTER TABLE analysis_memory ADD COLUMN risk_affinity text;` ausführen (sonst schlägt jeder save_analysis-INSERT fehl).

---

### Task 9: Billiger Recompute aus gespeicherten Bausteinen

**Files:**
- Create: `core/utils/bond_recompute.py`
- Test: `tests/utils/test_bond_recompute.py`

**Interfaces:**
- Consumes: `aggregate_bond_signal` (Task 2); ein Bausteine-Dict wie im `indicators_snapshot` (Task 8).
- Produces: `recompute_bond_signal(blocks: dict, new_affinity: RiskAffinity) -> tuple[Signal, float]` — rechnet das Gesamtsignal aus gespeicherten Bausteinen + neuer Affinität neu, OHNE Datenabfrage.

- [ ] **Step 1: Failing test**

```python
# tests/utils/test_bond_recompute.py
from core.domain.models import Signal, RiskAffinity
from core.utils.bond_recompute import recompute_bond_signal


def _blocks():
    return {"bond_credit_band": "mittel", "bond_metrics_signal": "bullish",
            "bond_duration_signal": "neutral", "bond_spread_signal": "neutral"}


def test_recompute_aendert_signal_mit_affinitaet():
    assert recompute_bond_signal(_blocks(), RiskAffinity.RISIKOFREUDIG)[0] == Signal.BULLISH
    assert recompute_bond_signal(_blocks(), RiskAffinity.KONSERVATIV)[0] == Signal.NEUTRAL


def test_recompute_ohne_band_renormalisiert():
    blocks = {"bond_metrics_signal": "bullish", "bond_duration_signal": "bullish",
              "bond_spread_signal": "neutral"}
    assert recompute_bond_signal(blocks, RiskAffinity.NEUTRAL)[0] == Signal.BULLISH
```

- [ ] **Step 2: Run → fail**.

- [ ] **Step 3: Implement** — `core/utils/bond_recompute.py`:

```python
from core.domain.models import Signal, RiskAffinity, CreditBand
from core.utils.bond_risk import aggregate_bond_signal


def _sig(v: str | None) -> Signal | None:
    return Signal(v) if v is not None else None


def recompute_bond_signal(blocks: dict, new_affinity: RiskAffinity) -> tuple[Signal, float]:
    """Gesamtsignal aus gespeicherten Bausteinen + neuer Risikoaffinität neu rechnen
    (kein Datenabruf). Bausteine entsprechen dem indicators_snapshot aus save_analysis."""
    band_v = blocks.get("bond_credit_band")
    band = CreditBand(band_v) if band_v is not None else None
    return aggregate_bond_signal(
        _sig(blocks.get("bond_metrics_signal")),
        _sig(blocks.get("bond_duration_signal")),
        _sig(blocks.get("bond_spread_signal")),
        band,
        new_affinity,
    )
```

- [ ] **Step 4: Run → pass**.

- [ ] **Step 5: Commit**

```bash
git add core/utils/bond_recompute.py tests/utils/test_bond_recompute.py
git commit -m "feat(bond): billiger Recompute des Gesamtsignals aus gespeicherten Bausteinen"
```

---

## Abschluss

- [ ] **Gesamtsuite grün:** `python -m pytest -q` — Ergebnis nennen.
- [ ] Logbuch `docs/open_todos.md`: Bond-Risikoaffinität als erledigt vermerken (Verweis auf Spec + Plan); der kleine #47-Rest `commodity_chief_mikro` bleibt separate Mini-PR (eigener Eintrag).

## Self-Review (gegen den Spec)

- §3.1 Bänder → Task 2 (`rating_to_band`). §3.2 Tabelle → Task 2. §3.3/3.4 Aggregation + Unverfügbarkeit → Task 2. §3.5 Beispiele → Task 2 Tests. §4.1 Enums/Modelle → Task 1+3+6. §4.3 `credit.sp` → bereits vorhanden, in Task 4 genutzt. §4.4 Chief → Task 4. §4.5 CLI-Pflicht → Task 5. §4.6 Persistenz → Task 8. §4.7 Portfolio → Task 6. §4.8 Recompute → Task 9. §4.9 Monitor → Task 7. §7 Migration → Task 8.
- Hinweis: Bond-Sub-Snapshots tragen immer ein `signal` (kein eigener Status) → nur `credit_band=None` löst den Unverfügbar-Pfad aus (in Task 2/4 berücksichtigt).
