# Anlageklassen-Taxonomie Phase 1 (Fundament) — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans, um diesen Plan Task-für-Task umzusetzen. Schritte nutzen Checkbox-Syntax (`- [ ]`) zur Nachverfolgung.

**Goal:** Das überladene Feld `asset_class: str` durch **zwei orthogonale Achsen** ersetzen — `underlying` (wählt die Analyse-Engine) und `wrapper` (Hülle/Mechanik) — verhaltens-erhaltend, und dabei den stillen `etf`→Equity-Durchfall-Bug strukturell beheben.

**Architecture:** Zwei `str`-Enums in `core/domain/` (reine Domäne, keine I/O). Ein **Übergangs-Bruch-freier** Umbau: jedes Modell trägt künftig `underlying`+`wrapper`; eine **abgeleitete Read-`@property asset_class`** hält noch-nicht-migrierte Konsumenten grün, bis sie Task für Task auf die Achsen umgestellt sind; im Schluss-Task fällt die Property weg. Dispatch im `BottomUpOrchestrator` schaltet von String-`if`-Kette auf `underlying`.

**Tech Stack:** Python 3.12, `dataclasses`, `enum` (`class X(str, Enum)`), pytest. Reiner Domänen-/Orchestrator-Code, keine neuen externen Libs.

## Global Constraints

- **Sprache:** Code-Kommentare + Commit-Messages **Deutsch** (AGENTS.md §0).
- **TDD Pflicht** (AGENTS.md §4): erst fehlschlagender Test (Rot) → minimal grün → aufräumen. Kein Code ohne vorher geschriebenen Test.
- **Hexagonal** (AGENTS.md §1): Enums + Modelle bleiben in `core/domain/`, **keine** I/O dort.
- **Lückenlose Klassifizierung** (AGENTS.md §2): jede `(underlying, wrapper)`-Kombination fällt in genau einen `_short_type`-Zweig (§8.4-Matrix der Spec).
- **Verhaltens-erhaltend:** Für `wrapper ∈ {single, fund}` liefern die 5 Bestands-Engines **identische** Ergebnisse wie vorher. **Ausnahme & gewollt:** `etf`→jetzt Index-Engine (XLE), nicht mehr Equity (Spec §11, §9).
- **Netz in Tests blockiert** (`tests/conftest.py`, aus PR #31) — keine echten Calls; Provider mocken.
- **Quelle der Wahrheit:** `docs/superpowers/specs/2026-06-21-anlageklassen-taxonomie-design.md` (Design/Entscheidungen §13) + `…-impact.md` (Folgen). Dieser Plan setzt **nur Phase 1** (Spec §10) um.
- **Vor jedem „fertig":** `python -m pytest -q` grün, Ergebnis nennen.

---

## File Structure

| Datei | Verantwortung | Task |
|---|---|---|
| `core/domain/taxonomy.py` (neu) | `Underlying`-/`Wrapper`-Enums + Legacy-Mapper (`legacy_to_taxonomy`, `legacy_asset_class`) | 1 |
| `core/domain/models.py` | `BottomUpResult`/`ShortAssessment`/`DeepDiveResult`: `asset_class` → `underlying`+`wrapper` + Übergangs-Property | 2, 8 |
| `orchestrators/bottom_up_orchestrator.py` | Dispatch über `underlying`; Konstruktion mit neuen Feldern | 2, 7 |
| `adapters/cache/result_cache.py` | `save_/load_bottom_up` symmetrisch um die zwei Felder | 2 |
| `agents/judgment/judgment_agent.py` | Durchreichen `underlying`/`wrapper` an Recommendation/Short/DeepDive | 2, 3, 4 |
| `core/domain/recommendation.py` | `_short_type(underlying, wrapper)` (§8.4-Matrix) statt `ETF_ASSET_CLASSES`; `derive_recommendation`-Signatur | 3 |
| `core/domain/short_assessment.py` | Fallback-Verzweigung auf `underlying` statt `asset_class` | 4 |
| `core/domain/top_down_context.py` | `_BUFFETT_RELEVANT_ASSETS` → `underlying ∈ {equity, equity_index}` | 5 |
| `core/domain/portfolio.py` + `adapters/persistence/json_portfolio.py` | `Position.underlying`+`wrapper` (Enum) + JSON-Lesung | 6 |
| `app/main.py` | CLI `bottomup`: `underlying`/`wrapper`-Argumente (+ Legacy-Kompat) | 7 |
| `tests/…` | je Task mit-angepasst; Round-Trip- + Reklassifizierungs-Tests | 2, 8 |

---

## Task 1: Taxonomie-Enums + Legacy-Mapper

**Files:**
- Create: `core/domain/taxonomy.py`
- Test: `tests/test_taxonomy.py`

**Interfaces:**
- Produces:
  - `class Underlying(str, Enum)` mit `EQUITY="equity"`, `EQUITY_INDEX="equity_index"`, `BOND="bond"`, `COMMODITY="commodity"`, `PRECIOUS_METAL="precious_metal"`.
  - `class Wrapper(str, Enum)` mit `SINGLE="single"`, `FUND="fund"`, `FUTURE="future"`, `PHYSICAL_ETC="physical_etc"`.
  - `legacy_to_taxonomy(asset_class: str) -> tuple[Underlying, Wrapper]` (Mapping Spec §5).
  - `legacy_asset_class(underlying: Underlying, wrapper: Wrapper) -> str` (Rück-Abbildung für die Übergangs-Property; Inverse von §5 mit dokumentierter Konvention).

- [ ] **Step 1: Failing test schreiben** — `tests/test_taxonomy.py`

```python
import pytest
from core.domain.taxonomy import Underlying, Wrapper, legacy_to_taxonomy, legacy_asset_class


def test_enum_werte_sind_lesbare_strings():
    assert Underlying.EQUITY == "equity"
    assert Underlying.EQUITY_INDEX == "equity_index"
    assert Wrapper.FUTURE == "future"
    assert Wrapper.PHYSICAL_ETC == "physical_etc"


@pytest.mark.parametrize("legacy, expected", [
    ("equity",         (Underlying.EQUITY,         Wrapper.SINGLE)),
    ("etf",            (Underlying.EQUITY_INDEX,   Wrapper.FUND)),     # behebt den Durchfall-Bug
    ("index",          (Underlying.EQUITY_INDEX,   Wrapper.SINGLE)),
    ("bond",           (Underlying.BOND,           Wrapper.SINGLE)),
    ("commodity",      (Underlying.COMMODITY,      Wrapper.FUTURE)),
    ("precious_metal", (Underlying.PRECIOUS_METAL, Wrapper.FUTURE)),
    ("EQUITY",         (Underlying.EQUITY,         Wrapper.SINGLE)),    # case-insensitiv
])
def test_legacy_to_taxonomy(legacy, expected):
    assert legacy_to_taxonomy(legacy) == expected


def test_legacy_to_taxonomy_unbekannt_faellt_auf_equity_single():
    # Unbekannter Alt-Wert: defensiver Default (kein Crash an der Eingangsgrenze).
    assert legacy_to_taxonomy("hudelei") == (Underlying.EQUITY, Wrapper.SINGLE)


@pytest.mark.parametrize("underlying, wrapper, expected", [
    (Underlying.EQUITY,         Wrapper.SINGLE, "equity"),
    (Underlying.EQUITY_INDEX,   Wrapper.FUND,   "etf"),
    (Underlying.EQUITY_INDEX,   Wrapper.SINGLE, "index"),
    (Underlying.BOND,           Wrapper.SINGLE, "bond"),
    (Underlying.COMMODITY,      Wrapper.FUTURE, "commodity"),
    (Underlying.PRECIOUS_METAL, Wrapper.FUTURE, "precious_metal"),
    (Underlying.PRECIOUS_METAL, Wrapper.PHYSICAL_ETC, "precious_metal"),  # ETC nutzt PM-Engine
])
def test_legacy_asset_class_rueckabbildung(underlying, wrapper, expected):
    assert legacy_asset_class(underlying, wrapper) == expected
```

- [ ] **Step 2: Test läuft rot**

Run: `python -m pytest tests/test_taxonomy.py -q`
Expected: FAIL — `ModuleNotFoundError: core.domain.taxonomy`.

- [ ] **Step 3: Implementierung** — `core/domain/taxonomy.py`

```python
"""Anlageklassen-Taxonomie: zwei orthogonale Achsen statt eines überladenen `asset_class`.

`underlying` wählt die Analyse-Engine (WAS treibt P&L?), `wrapper` die Mechanik-Schicht
(WIE gehalten?). Siehe docs/superpowers/specs/2026-06-21-anlageklassen-taxonomie-design.md.
Reine Domäne — keine I/O.
"""
from enum import Enum


class Underlying(str, Enum):
    """Basiswert → wählt die Bottom-Up-Engine."""
    EQUITY         = "equity"          # Einzelaktie (inkl. Rohstoff-/Minenkonzerne)
    EQUITY_INDEX   = "equity_index"    # Aktienindex / Aktien-Sektorkorb (vormals "index")
    BOND           = "bond"
    COMMODITY      = "commodity"       # physischer Rohstoff (Öl, Gas, Agrar, Industriemetall)
    PRECIOUS_METAL = "precious_metal"  # Gold, Silber, Platin, Palladium


class Wrapper(str, Enum):
    """Hülle → schaltet eine Risiko-/Mechanik-Schicht zu (Phase 2)."""
    SINGLE       = "single"        # Einzelwert / direktes Wertpapier
    FUND         = "fund"          # Fonds/ETF (Korb)
    FUTURE       = "future"        # Terminkontrakt (Hebel, Roll, Verfall)
    PHYSICAL_ETC = "physical_etc"  # physisch hinterlegtes Rohstoff-ETC (reiner Spot)


# Alt-String → (underlying, wrapper). Mapping gemäß Spec §5. Behebt den `etf`-Durchfall:
# "etf" wird zu equity_index/fund (Index-Engine), nicht mehr stillschweigend Equity.
_LEGACY_MAP: dict[str, tuple[Underlying, Wrapper]] = {
    "equity":         (Underlying.EQUITY,         Wrapper.SINGLE),
    "etf":            (Underlying.EQUITY_INDEX,   Wrapper.FUND),
    "index":          (Underlying.EQUITY_INDEX,   Wrapper.SINGLE),
    "bond":           (Underlying.BOND,           Wrapper.SINGLE),
    "commodity":      (Underlying.COMMODITY,      Wrapper.FUTURE),
    "precious_metal": (Underlying.PRECIOUS_METAL, Wrapper.FUTURE),
}


def legacy_to_taxonomy(asset_class: str) -> tuple[Underlying, Wrapper]:
    """Alt-`asset_class`-String → (underlying, wrapper). Unbekannt → equity/single (defensiv)."""
    return _LEGACY_MAP.get((asset_class or "").lower(), (Underlying.EQUITY, Wrapper.SINGLE))


def legacy_asset_class(underlying: Underlying, wrapper: Wrapper) -> str:
    """Rück-Abbildung für die Übergangs-Property `BottomUpResult.asset_class`.

    Konvention (eindeutig pro Engine, deckt den Phase-1-Umfang ab):
    equity→"equity", bond→"bond", commodity→"commodity", precious_metal→"precious_metal"
    (Engine ist hüllenunabhängig dieselbe); equity_index→"etf" bei wrapper=fund, sonst "index".
    """
    if underlying == Underlying.EQUITY_INDEX:
        return "etf" if wrapper == Wrapper.FUND else "index"
    return underlying.value
```

- [ ] **Step 4: Test läuft grün**

Run: `python -m pytest tests/test_taxonomy.py -q`
Expected: PASS (alle Parametrierungen).

- [ ] **Step 5: Commit**

```bash
git add core/domain/taxonomy.py tests/test_taxonomy.py
git commit -m "feat(taxonomie): Underlying/Wrapper-Enums + Legacy-Mapper (Phase 1, Fundament)"
```

---

## Task 2: Modelle tragen `underlying`+`wrapper` (mit Übergangs-Property) — verhaltens-erhaltend

**Files:**
- Modify: `core/domain/models.py` (`BottomUpResult` ~749, `ShortAssessment` ~808, `DeepDiveResult` ~829)
- Modify: `orchestrators/bottom_up_orchestrator.py` (Konstruktion in `_run_*`, vorerst Dispatch noch per `asset_class`-Param via Mapper)
- Modify: `adapters/cache/result_cache.py` (`save_bottom_up`/`load_bottom_up`)
- Modify: `agents/judgment/judgment_agent.py` (Konstruktion `DeepDiveResult`/`ShortAssessment`)
- Test: `tests/test_taxonomy_model_roundtrip.py` (neu) + Anpassung bestehender Konstruktions-Tests

**Interfaces:**
- Consumes: `Underlying`, `Wrapper`, `legacy_to_taxonomy`, `legacy_asset_class` (Task 1).
- Produces:
  - `BottomUpResult.underlying: Underlying`, `BottomUpResult.wrapper: Wrapper` (statt `asset_class`); **Übergangs**-`@property asset_class -> str` (Read-only, via `legacy_asset_class`). Analog `ShortAssessment` und `DeepDiveResult`.
  - Konvention: `underlying`/`wrapper` sind **die ersten beiden Felder nach `ticker`** (ersetzen `asset_class` an gleicher Position), damit positionsbasierte Konstruktion eindeutig bleibt.

**Hintergrund (Spec §S/§4-Impact):** Hier entstand früher Bug #1 (asymmetrisches save/load). Der Round-Trip-Test schließt diese Lücke **in diesem Task**.

- [ ] **Step 1: Failing Round-Trip-Test** — `tests/test_taxonomy_model_roundtrip.py`

```python
from core.domain.taxonomy import Underlying, Wrapper
from core.domain.models import BottomUpResult


def _minimal_bottom_up(underlying, wrapper):
    return BottomUpResult(
        ticker="X", underlying=underlying, wrapper=wrapper,
        fundamentals=None, quality=None, short_interest=None, insider=None,
        earnings_trend=None, moat=None, valuation_range=None,
        precious_metals=None, bond=None, index=None, commodity_deep=None,
    )


def test_underlying_wrapper_gesetzt_und_property_leitet_ab():
    r = _minimal_bottom_up(Underlying.EQUITY_INDEX, Wrapper.FUND)
    assert r.underlying == Underlying.EQUITY_INDEX
    assert r.wrapper == Wrapper.FUND
    assert r.asset_class == "etf"   # Übergangs-Property (Read-only)


def test_cache_roundtrip_erhaelt_underlying_wrapper():
    # Schließt die offene Round-Trip-Lücke (Bug-#1-Typ): save→load muss beide Felder erhalten.
    from adapters.cache.result_cache import ResultCache
    cache = ResultCache(redis_client=None)   # In-Memory-Fallback (siehe ResultCache)
    original = _minimal_bottom_up(Underlying.COMMODITY, Wrapper.FUTURE)
    cache.save_bottom_up("CL", original)
    loaded = cache.load_bottom_up("CL")
    assert loaded.underlying == Underlying.COMMODITY
    assert loaded.wrapper == Wrapper.FUTURE
```

> **Hinweis für den Umsetzer:** `ResultCache`-Konstruktor + In-Memory-Verhalten vorher in `adapters/cache/result_cache.py` prüfen und den Aufruf exakt an die dortige Signatur anpassen (z. B. bestehendes Test-Setup in `tests/` spiegeln). Der Test-Kern (save→load erhält beide Felder) bleibt.

- [ ] **Step 2: Test läuft rot**

Run: `python -m pytest tests/test_taxonomy_model_roundtrip.py -q`
Expected: FAIL — `TypeError: __init__ got unexpected keyword 'underlying'` (Feld existiert noch nicht).

- [ ] **Step 3a: Modelle umstellen** — `core/domain/models.py`

In `BottomUpResult` (und analog `ShortAssessment`, `DeepDiveResult`) die Zeile `asset_class: str` ersetzen durch:

```python
    underlying: "Underlying"
    wrapper: "Wrapper"
```

Oben in `models.py` importieren: `from core.domain.taxonomy import Underlying, Wrapper, legacy_asset_class`. In **jede** der drei Dataclasses die Übergangs-Property einfügen (Read-only; hält noch-nicht-migrierte Konsumenten grün):

```python
    @property
    def asset_class(self) -> str:
        """ÜBERGANG (Phase 1): abgeleiteter Alt-String, bis alle Konsumenten auf
        underlying/wrapper umgestellt sind. Wird in Task 8 entfernt."""
        return legacy_asset_class(self.underlying, self.wrapper)
```

> **Achtung Dataclass:** Eine `@property asset_class` darf **nicht** mit einem gleichnamigen Feld kollidieren — deshalb wird das Feld `asset_class` **entfernt** und nur die Property bleibt. `ShortAssessment`/`DeepDiveResult` tragen `underlying`/`wrapper` analog als erste Felder.

- [ ] **Step 3b: Orchestrator-Konstruktion umstellen** — `orchestrators/bottom_up_orchestrator.py`

`run(...)` nimmt in Phase 1 weiterhin `asset_class: str` (CLI-Umstellung erst Task 7), leitet aber **intern** ab. Am Anfang von `run`:

```python
from core.domain.taxonomy import legacy_to_taxonomy
underlying, wrapper = legacy_to_taxonomy(asset_class)
```

In **jeder** `_run_*`-Methode die Konstruktion `BottomUpResult(ticker=…, asset_class="…", …)` ersetzen durch `underlying=…, wrapper=…`. Konkrete Werte je Methode (verhaltens-erhaltend, via §5):
- `_run_equity`: `underlying=Underlying.EQUITY, wrapper=Wrapper.SINGLE` (Hinweis: das alte `_run_equity` reichte `asset_class` durch — in Phase 1 fix `equity/single`, da `etf` nun **nicht** mehr hier landet, sondern via Dispatch in den Index-Zweig).
- `_run_bond`: `Underlying.BOND, Wrapper.SINGLE`
- `_run_index`: `Underlying.EQUITY_INDEX` + `wrapper` aus dem Aufruf (`single` oder `fund`)
- `_run_commodity`: `Underlying.COMMODITY, Wrapper.FUTURE`
- `_run_precious_metals`: `Underlying.PRECIOUS_METAL, Wrapper.FUTURE`

Die Methoden-Signaturen der `_run_*` nehmen künftig `underlying`/`wrapper` statt `asset_class` durch. **Dispatch bleibt** in diesem Task noch String-basiert (`if asset_class == …`) — die Umstellung auf `match underlying` erfolgt in Task 7 gemeinsam mit der CLI; so bleibt Task 2 fokussiert.

> **Reklassifizierung `etf`:** Dispatch um einen Zweig ergänzen, **bevor** der Equity-Default greift:
> ```python
> if asset_class in ("index", "etf"):
>     wrapper = Wrapper.FUND if asset_class == "etf" else Wrapper.SINGLE
>     return await self._run_index(ticker, wrapper)
> ```
> Damit landet XLE (`etf`) in der **Index-Engine** (Bug behoben). `_run_index` nimmt `wrapper` entgegen.

- [ ] **Step 3c: Cache + judgment_agent symmetrisch** — `adapters/cache/result_cache.py`, `agents/judgment/judgment_agent.py`

- `save_bottom_up`/`load_bottom_up`: das serialisierte Dict um `"underlying"`/`"wrapper"` erweitern (Werte als `.value`-Strings schreiben, beim Laden via `Underlying(...)`/`Wrapper(...)` zurückwandeln) und `asset_class` aus dem Serialisierungs-Dict **entfernen**. Symmetrie zwingend (Bug #1).
- `judgment_agent.py`: wo `bottom_up.asset_class` an `DeepDiveResult(...)`/`ShortAssessment(...)` durchgereicht wird, stattdessen `underlying=bottom_up.underlying, wrapper=bottom_up.wrapper` setzen. (Konsumenten `derive_recommendation`/`derive_short_assessment` lesen vorerst über die Übergangs-`.asset_class`-Property → grün; echte Umstellung Task 3/4.)

- [ ] **Step 4: Tests grün** — Round-Trip + Gesamtsuite

Run: `python -m pytest tests/test_taxonomy_model_roundtrip.py -q` → PASS.
Run: `python -m pytest -q` → bestehende Tests, die `BottomUpResult(..., asset_class=…)` konstruieren, müssen auf `underlying=…, wrapper=…` umgestellt werden (mechanisch; Werte via §5). Lauf grün.
Expected: alle grün (Konsumenten lesen über die Übergangs-Property).

- [ ] **Step 5: Commit**

```bash
git add core/domain/models.py orchestrators/bottom_up_orchestrator.py adapters/cache/result_cache.py agents/judgment/judgment_agent.py tests/
git commit -m "feat(taxonomie): Modelle auf underlying+wrapper + Cache-Round-Trip (Übergangs-Property, verhaltens-erhaltend)"
```

---

## Task 3: `recommendation` — `_short_type(underlying, wrapper)` per §8.4-Matrix

**Files:**
- Modify: `core/domain/recommendation.py` (Z. 31 `ETF_ASSET_CLASSES`, Z. 39-42 `_short_type`, Z. 110-119 `derive_recommendation`-Signatur)
- Modify: `agents/judgment/judgment_agent.py` (Aufruf von `derive_recommendation`/`_short_type`)
- Test: `tests/test_recommendation_taxonomy.py` (existiert — erweitern)

**Interfaces:**
- Consumes: `Underlying`, `Wrapper` (Task 1); `bottom_up.underlying`/`.wrapper` (Task 2).
- Produces: `_short_type(underlying: Underlying, wrapper: Wrapper) -> ShortType`; `derive_recommendation(..., underlying, wrapper, ...)`.

**Regel (Spec §8.4):** *Defensiv* = `underlying == EQUITY_INDEX` **oder** `wrapper == FUND`; alles andere = *Aggressiv*. Ersetzt `ETF_ASSET_CLASSES`/`AGGRESSIVE_ASSET_CLASSES`.

- [ ] **Step 1: Failing test** — in `tests/test_recommendation_taxonomy.py` ergänzen

```python
import pytest
from core.domain.taxonomy import Underlying, Wrapper
from core.domain.recommendation import _short_type
from core.domain.models import ShortType


@pytest.mark.parametrize("underlying, wrapper, expected", [
    (Underlying.EQUITY,         Wrapper.SINGLE,       ShortType.AGGRESSIVE),
    (Underlying.EQUITY,         Wrapper.FUND,         ShortType.DEFENSIVE),   # Aktien-ETF = breit
    (Underlying.EQUITY_INDEX,   Wrapper.SINGLE,       ShortType.DEFENSIVE),
    (Underlying.EQUITY_INDEX,   Wrapper.FUND,         ShortType.DEFENSIVE),
    (Underlying.EQUITY_INDEX,   Wrapper.FUTURE,       ShortType.DEFENSIVE),   # Index-Future bleibt breit
    (Underlying.BOND,           Wrapper.SINGLE,       ShortType.AGGRESSIVE),
    (Underlying.BOND,           Wrapper.FUND,         ShortType.DEFENSIVE),
    (Underlying.COMMODITY,      Wrapper.FUTURE,       ShortType.AGGRESSIVE),
    (Underlying.PRECIOUS_METAL, Wrapper.FUTURE,       ShortType.AGGRESSIVE),
    (Underlying.PRECIOUS_METAL, Wrapper.PHYSICAL_ETC, ShortType.AGGRESSIVE),
])
def test_short_type_matrix(underlying, wrapper, expected):
    assert _short_type(underlying, wrapper) == expected
```

- [ ] **Step 2: Rot**

Run: `python -m pytest tests/test_recommendation_taxonomy.py -q`
Expected: FAIL — `_short_type` nimmt heute 1 Arg (`asset_class`), Test ruft mit 2.

- [ ] **Step 3: Implementierung** — `core/domain/recommendation.py`

`ETF_ASSET_CLASSES = {"etf", "index"}` (Z. 31) **entfernen**. `_short_type` ersetzen:

```python
from core.domain.taxonomy import Underlying, Wrapper

def _short_type(underlying: Underlying, wrapper: Wrapper) -> ShortType:
    # Defensiv (marktbreite Absicherung): Aktienindex ODER Fonds-Hülle. Sonst aggressiv
    # (gezielte Einzel-/Future-Wette). Spec §8.4 — ersetzt die alten String-Mengen.
    if underlying == Underlying.EQUITY_INDEX or wrapper == Wrapper.FUND:
        return ShortType.DEFENSIVE
    return ShortType.AGGRESSIVE
```

`derive_recommendation`-Signatur: `asset_class: str` ersetzen durch `underlying: Underlying, wrapper: Wrapper`. (Im aktuellen Rumpf wird `asset_class` nur potentiell für den Short-Typ gebraucht — sicherstellen, dass jeder `_short_type`-Aufruf jetzt `(underlying, wrapper)` übergibt.) `judgment_agent.py`: den Aufruf `derive_recommendation(..., asset_class=…)` auf `underlying=bottom_up.underlying, wrapper=bottom_up.wrapper` umstellen.

- [ ] **Step 4: Grün**

Run: `python -m pytest tests/test_recommendation_taxonomy.py tests/test_recommendation.py -q` → PASS.
Run: `python -m pytest -q` → grün.

- [ ] **Step 5: Commit**

```bash
git add core/domain/recommendation.py agents/judgment/judgment_agent.py tests/test_recommendation_taxonomy.py
git commit -m "feat(taxonomie): _short_type über (underlying, wrapper)-Matrix statt ETF_ASSET_CLASSES (§8.4)"
```

---

## Task 4: `short_assessment` — Fallback-Verzweigung über `underlying`

**Files:**
- Modify: `core/domain/short_assessment.py` (Z. 50 `_mk`, Z. 57-67 `derive_short_assessment`)
- Modify: `agents/judgment/judgment_agent.py` (Aufruf — bereits `bottom_up` übergeben; sicherstellen `underlying` lesbar)
- Test: `tests/test_short_assessment_engine.py` (existiert — anpassen)

**Interfaces:**
- Consumes: `Underlying` (Task 1); `bottom_up.underlying` (Task 2).
- Produces: `ShortAssessment` trägt `underlying`/`wrapper` (statt `asset_class`); Verzweigung `if underlying != Underlying.EQUITY` (verhaltens-erhaltend: Nicht-Equity → bestehender neutraler Fallback).

- [ ] **Step 1: Failing test** — `tests/test_short_assessment_engine.py` anpassen

Bestehenden Nicht-Equity-Fallback-Test auf das neue Schema umstellen; Kern:

```python
from core.domain.taxonomy import Underlying, Wrapper
from core.domain.models import PositionState, ShortAction

def test_nicht_equity_unterlying_faellt_neutral_zurueck():
    bottom_up = _bottom_up(underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE)  # Helfer im Test
    res = derive_short_assessment(bottom_up, cockpit=None, current_position=PositionState.NONE,
                                  top_down_available=True, bu_anomaly=None, td_anomaly=None)
    assert res.short_action == ShortAction.NONE
    assert res.confidence == 0.10
    assert res.underlying == Underlying.COMMODITY
```

> Den lokalen `_bottom_up`-Helfer im Test auf `underlying`/`wrapper` umstellen (statt `asset_class`).

- [ ] **Step 2: Rot**

Run: `python -m pytest tests/test_short_assessment_engine.py -q`
Expected: FAIL — `derive_short_assessment` liest `getattr(bottom_up, "asset_class", …)` und verzweigt per String; `ShortAssessment` kennt `underlying` noch nicht im Konstruktor `_mk`.

- [ ] **Step 3: Implementierung** — `core/domain/short_assessment.py`

- Import: `from core.domain.taxonomy import Underlying, Wrapper`.
- Z. 60: `asset_class = getattr(bottom_up, "asset_class", "equity")` ersetzen durch:
  ```python
  underlying = getattr(bottom_up, "underlying", Underlying.EQUITY)
  wrapper = getattr(bottom_up, "wrapper", Wrapper.SINGLE)
  ```
- Z. 64: `if asset_class != "equity":` → `if underlying != Underlying.EQUITY:`.
- `_mk(...)`: erstes Argument `asset_class` ersetzen durch `underlying, wrapper`; im `ShortAssessment(...)` `asset_class=asset_class` → `underlying=underlying, wrapper=wrapper`. Alle `_mk(asset_class, …)`-Aufrufe entsprechend auf `_mk(underlying, wrapper, …)` umstellen.

- [ ] **Step 4: Grün**

Run: `python -m pytest tests/test_short_assessment_engine.py tests/test_short_assessment_model.py -q` → PASS.
Run: `python -m pytest -q` → grün.

- [ ] **Step 5: Commit**

```bash
git add core/domain/short_assessment.py agents/judgment/judgment_agent.py tests/test_short_assessment_engine.py
git commit -m "feat(taxonomie): short_assessment verzweigt über underlying (verhaltens-erhaltend)"
```

---

## Task 5: `top_down_context` — Buffett-Relevanz über `underlying`

**Files:**
- Modify: `core/domain/top_down_context.py` (`_BUFFETT_RELEVANT_ASSETS`, Konsument)
- Test: `tests/test_domain_extensions.py` o. ä. (Buffett-Relevanz-Test — anpassen/ergänzen)

**Interfaces:**
- Consumes: `Underlying` (Task 1).
- Produces: Buffett-Relevanz über `underlying ∈ {EQUITY, EQUITY_INDEX}` (fachlich identisch: Marktkap./BIP nur für aktienartige Werte).

- [ ] **Step 1: Failing test**

```python
from core.domain.taxonomy import Underlying

def test_buffett_relevant_nur_fuer_aktienartige_underlyings():
    from core.domain.top_down_context import _is_buffett_relevant  # ggf. Helfer/Funktion spiegeln
    assert _is_buffett_relevant(Underlying.EQUITY) is True
    assert _is_buffett_relevant(Underlying.EQUITY_INDEX) is True
    assert _is_buffett_relevant(Underlying.BOND) is False
    assert _is_buffett_relevant(Underlying.COMMODITY) is False
    assert _is_buffett_relevant(Underlying.PRECIOUS_METAL) is False
```

> **Umsetzer:** Die genaue Konsumstelle in `top_down_context.py` lesen — heute `_BUFFETT_RELEVANT_ASSETS = {"equity","etf","index"}` + ein String-Vergleich. Den Test an die dort vorhandene Funktion/Bedingung anpassen (oder einen kleinen reinen Helfer `_is_buffett_relevant(underlying)` extrahieren und beidseitig nutzen).

- [ ] **Step 2: Rot** → Run: `python -m pytest tests/test_domain_extensions.py -q` → FAIL.

- [ ] **Step 3: Implementierung** — `core/domain/top_down_context.py`

```python
from core.domain.taxonomy import Underlying
_BUFFETT_RELEVANT_UNDERLYINGS = {Underlying.EQUITY, Underlying.EQUITY_INDEX}
```

Die Konsumstelle von `asset_class in _BUFFETT_RELEVANT_ASSETS` auf `underlying in _BUFFETT_RELEVANT_UNDERLYINGS` umstellen (Aufrufer übergibt künftig `underlying` statt `asset_class`).

- [ ] **Step 4: Grün** → `python -m pytest -q` grün.

- [ ] **Step 5: Commit**

```bash
git add core/domain/top_down_context.py tests/test_domain_extensions.py
git commit -m "feat(taxonomie): Buffett-Relevanz über underlying ∈ {equity, equity_index}"
```

---

## Task 6: `Position` + JSON-Portfolio — `underlying`+`wrapper`

**Files:**
- Modify: `core/domain/portfolio.py` (`Position`, Z. 16 `asset_class`)
- Modify: `adapters/persistence/json_portfolio.py` (Lesung)
- Test: `tests/test_json_portfolio.py`, `tests/agents/portfolio/…` (anpassen)

**Interfaces:**
- Consumes: `Underlying`, `Wrapper`, `legacy_to_taxonomy` (Task 1).
- Produces: `Position.underlying: Underlying = Underlying.EQUITY`, `Position.wrapper: Wrapper = Wrapper.SINGLE`. `JsonPortfolioProvider` liest `underlying`/`wrapper` aus JSON; Alt-Schlüssel `asset_class` wird via `legacy_to_taxonomy` abwärtskompatibel abgebildet.

- [ ] **Step 1: Failing test** — `tests/test_json_portfolio.py`

```python
from core.domain.taxonomy import Underlying, Wrapper

def test_position_default_und_legacy_asset_class(tmp_path):
    # (a) Neues Schema: underlying/wrapper direkt; (b) Alt-Schlüssel asset_class → gemappt.
    import json
    p = tmp_path / "portfolio.json"
    p.write_text(json.dumps({"positions": [
        {"ticker": "GC", "shares": 1, "buy_price": 1800, "direction": "long",
         "underlying": "precious_metal", "wrapper": "future"},
        {"ticker": "XLE", "shares": 1, "buy_price": 80, "direction": "long",
         "asset_class": "etf"},   # Legacy
    ]}), encoding="utf-8")
    positions = JsonPortfolioProvider(str(p)).load_positions()  # an reale Signatur anpassen
    assert positions[0].underlying == Underlying.PRECIOUS_METAL and positions[0].wrapper == Wrapper.FUTURE
    assert positions[1].underlying == Underlying.EQUITY_INDEX and positions[1].wrapper == Wrapper.FUND
```

> **Umsetzer:** `JsonPortfolioProvider` (Klassenname/Methoden) in `adapters/persistence/json_portfolio.py` prüfen und Aufruf anpassen; `data/portfolio.json` ist leer → keine Bestandsmigration.

- [ ] **Step 2: Rot** → `python -m pytest tests/test_json_portfolio.py -q` → FAIL.

- [ ] **Step 3: Implementierung**

`core/domain/portfolio.py` — Z. 16 `asset_class: str = "equity"` ersetzen durch:
```python
from core.domain.taxonomy import Underlying, Wrapper
    underlying: Underlying = Underlying.EQUITY
    wrapper: Wrapper = Wrapper.SINGLE
```
`json_portfolio.py` — beim Bauen jeder `Position`: wenn `underlying`/`wrapper` im JSON vorhanden → `Underlying(raw)`/`Wrapper(raw)`; sonst wenn Alt-`asset_class` vorhanden → `legacy_to_taxonomy(raw)`; sonst Defaults. Unbekannter Enum-Wert → wie bei `direction` (PR #7 F3) **fail-loud** mit klarer Meldung.

- [ ] **Step 4: Grün** → `python -m pytest -q` grün.

- [ ] **Step 5: Commit**

```bash
git add core/domain/portfolio.py adapters/persistence/json_portfolio.py tests/
git commit -m "feat(taxonomie): Position trägt underlying+wrapper (Enum) + Legacy-JSON-Kompat"
```

---

## Task 7: CLI + Orchestrator-Dispatch auf `underlying`

**Files:**
- Modify: `app/main.py` (Doku-String Z. 4,9; `run_bottom_up` Z. 95-116; Dispatch Z. 232-245; `_parse_risk_affinity` Z. 35-47)
- Modify: `orchestrators/bottom_up_orchestrator.py` (`run`-Dispatch String-`if` → `match underlying`)
- Test: `tests/` für CLI/Orchestrator-Dispatch (neu/anpassen)

**Interfaces:**
- Consumes: `Underlying`, `Wrapper`, `legacy_to_taxonomy` (Task 1).
- Produces: `BottomUpOrchestrator.run(ticker, underlying: Underlying, wrapper: Wrapper, sector, bond_type, rate_direction, risk_affinity)`; CLI akzeptiert `bottomup TICKER [underlying] [wrapper] [sector] …` **und** den Alt-Aufruf `bottomup TICKER equity` (Legacy-String → via Mapper).

- [ ] **Step 1: Failing test** — Dispatch + CLI-Kompat

```python
import asyncio
from unittest.mock import MagicMock, AsyncMock
from core.domain.taxonomy import Underlying, Wrapper

def test_dispatch_routet_je_underlying_zur_richtigen_engine():
    orch = _orchestrator_mit_gemockten_chiefs()  # Helfer: alle Chiefs AsyncMock, default() gepatcht
    asyncio.run(orch.run("XLE", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.FUND))
    orch.index_chief.run.assert_awaited()        # XLE → Index-Engine, NICHT Equity
    orch.equity_chief.run.assert_not_awaited()
```

- [ ] **Step 2: Rot** → FAIL (`run` nimmt heute `asset_class`).

- [ ] **Step 3: Implementierung**

`bottom_up_orchestrator.py` — `run(...)`: `asset_class`-Param durch `underlying: Underlying, wrapper: Wrapper` ersetzen; den String-`if` durch `match underlying:` ersetzen (Index-Zweig nimmt `wrapper`):
```python
match underlying:
    case Underlying.PRECIOUS_METAL: return await self._run_precious_metals(ticker)
    case Underlying.BOND:           return await self._run_bond(ticker, bond_type, rate_direction, risk_affinity)
    case Underlying.EQUITY_INDEX:   return await self._run_index(ticker, wrapper)
    case Underlying.COMMODITY:      return await self._run_commodity(ticker)
    case _:                         return await self._run_equity(ticker)   # EQUITY
```
`app/main.py` — Doku-String auf `underlying | wrapper` + neue Werte; Argument-Parsing: `underlying`/`wrapper` aus `pos[2]`/`pos[3]` lesen. **Abwärtskompat:** ist `pos[2]` ein Alt-Wert (`equity|bond|commodity|precious_metal|etf|index`), via `legacy_to_taxonomy` auf `(underlying, wrapper)` mappen (so funktioniert `bottomup AAPL equity` weiter); sonst `Underlying(pos[2])`/`Wrapper(pos[3] or "single")`. `run_bottom_up` + `_parse_risk_affinity` von `asset_class` auf `underlying` umstellen (Bond-Pflicht: `underlying == Underlying.BOND`).

- [ ] **Step 4: Grün** → `python -m pytest -q` grün.

- [ ] **Step 5: Commit**

```bash
git add app/main.py orchestrators/bottom_up_orchestrator.py tests/
git commit -m "feat(taxonomie): Dispatch über match(underlying) + CLI underlying/wrapper (Legacy-kompat)"
```

---

## Task 8: Übergangs-Property entfernen + Reklassifizierungs-/Regressions-Sicherung

**Files:**
- Modify: `core/domain/models.py` (Übergangs-`@property asset_class` entfernen)
- Modify: alle verbliebenen Leser von `.asset_class` (Grep) → auf `underlying`/`wrapper` umstellen
- Test: `tests/test_taxonomy_reclassification.py` (neu)

**Interfaces:**
- Consumes: alle vorigen Tasks.
- Produces: **kein** `asset_class` mehr im Code (außer Legacy-Eingangs-Mapping in `taxonomy.py`/CLI/JSON).

- [ ] **Step 1: Reklassifizierungs-Test** — `tests/test_taxonomy_reclassification.py`

```python
import asyncio
from core.domain.taxonomy import Underlying, Wrapper

def test_xle_etf_landet_in_index_engine_nicht_equity():
    orch = _orchestrator_mit_gemockten_chiefs()
    res = asyncio.run(orch.run("XLE", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.FUND))
    assert res.underlying == Underlying.EQUITY_INDEX and res.wrapper == Wrapper.FUND
    orch.index_chief.run.assert_awaited()

def test_gold_future_vs_physical_etc_gleiche_pm_engine():
    orch = _orchestrator_mit_gemockten_chiefs()
    asyncio.run(orch.run("GC", underlying=Underlying.PRECIOUS_METAL, wrapper=Wrapper.FUTURE))
    asyncio.run(orch.run("GLD", underlying=Underlying.PRECIOUS_METAL, wrapper=Wrapper.PHYSICAL_ETC))
    assert orch.precious_metals_chief.run.await_count == 2   # beide → PM-Engine
```

- [ ] **Step 2: Property entfernen + verbliebene Leser finden**

Run: `git grep -n "\.asset_class\b"` und `git grep -n "asset_class"` — jeden verbliebenen **Leser** (nicht das Legacy-Eingangs-Mapping) auf `underlying`/`wrapper` umstellen. Dann die `@property asset_class` aus den drei Modellen in `models.py` entfernen.

- [ ] **Step 3: Lauf rot→grün**

Run: `python -m pytest -q`
Expected: Erst evtl. Fehler an verbliebenen Lesern → fixen, bis **alles grün**. Danach `git grep "asset_class"` zeigt nur noch Legacy-Mapping-Stellen (`taxonomy.py`, CLI-Parsing, JSON-Lesung).

- [ ] **Step 4: Volle Regression nennen**

Run: `python -m pytest -q`
Expected: vollständig grün; Ergebniszahl in der Zusammenfassung nennen (AGENTS.md §4).

- [ ] **Step 5: Commit**

```bash
git add -p   # gezielt: models.py + verbliebene Leser + neuer Test (KEIN git add -A)
git commit -m "feat(taxonomie): Übergangs-Property entfernt; Reklassifizierung XLE→Index abgesichert (Phase 1 fertig)"
```

---

## Self-Review-Notiz (gegen Spec geprüft)

- **Spec §10 Phase 1 abgedeckt:** Enums (T1), `BottomUpResult`/Dispatch (T2/T7), `recommendation`/`_short_type` (T3), `short_assessment`-Fallback (T4), `top_down_context` (T5), `Position` (T6), CLI (T7), Reklassifizierung XLE + `etf`-Durchfall behoben (T2/T8). ✅
- **Spec §S/Impact (Round-Trip, Bug-#1-Typ):** Cache-Symmetrie + Round-Trip-Test in T2. ✅
- **Spec §8.4-Matrix:** vollständig als Parametrier-Tabelle in T3 (lückenlos). ✅
- **Bewusst NICHT Phase 1:** `futures_mechanics`-Slot, `FuturesCurveProvider`-Port, `fund`-Info-Schicht, Short-Future-Zweig → **Phase 2/3** (eigene Pläne). Kein Platzhalter hier.
- **Supabase-Persistenz:** Falls `analysis_memory`/`portfolio_snapshots` `asset_class` serialisieren → in T2/T6 symmetrisch auf `underlying`/`wrapper` ziehen; **vor Deploy** `ALTER TABLE` prüfen (Impact §5.4). Umsetzer: `adapters/memory/supabase_memory.py` greppen.
- **Offene Mini-Annahme:** Exakte Signaturen von `ResultCache`, `JsonPortfolioProvider`, `top_down_context`-Konsument und `judgment_agent`-Durchreichung werden vom Umsetzer am Ist-Code verifiziert (Tests spiegeln sie). Die fachliche Transformation ist je Task vollständig vorgegeben.
