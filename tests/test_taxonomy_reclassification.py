"""TDD Task 8: Reklassifizierungs-Regressionssicherung.

Absichert:
- XLE (EQUITY_INDEX/FUND) → Index-Engine, NICHT Equity-Engine
- Gold als Future vs. physischem ETC → beide zur gleichen PM-Engine

Nutzt den gleichen _orchestrator_mit_gemockten_chiefs()-Helfer wie
test_bottom_up_dispatch.py, importiert ihn aber direkt aus dem dortigen Modul.
"""
import asyncio

from tests.test_bottom_up_dispatch import _orchestrator_mit_gemockten_chiefs
from core.domain.taxonomy import Underlying, Wrapper


def test_xle_etf_landet_in_index_engine_nicht_equity():
    """XLE (Energie-Sektor-ETF): underlying=EQUITY_INDEX, wrapper=FUND → index_chief.

    Phase-1-Kernbug-Fix: früher fiel 'etf' in die Equity-Engine. Jetzt muss
    EQUITY_INDEX/FUND explizit zur Index-Engine routen und darf die Equity-Engine
    NICHT aufrufen. Index-ETFs (XLE, SPY, QQQ) gehören fachlich zur Index-Engine,
    nicht zur Einzelaktien-Engine.
    """
    orch = _orchestrator_mit_gemockten_chiefs()
    result = asyncio.run(
        orch.run("XLE", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.FUND)
    )
    # Reklassifizierung korrekt: underlying/wrapper im Ergebnis erhalten
    assert result.underlying == Underlying.EQUITY_INDEX
    assert result.wrapper == Wrapper.FUND
    # Index-Engine wurde aufgerufen, Equity-Engine nicht
    orch.index_chief.run.assert_awaited()
    orch.equity_chief.run.assert_not_awaited()


def test_gold_future_und_physical_etc_beide_zur_pm_engine():
    """Gold-Future (GC) und Gold-ETC (GLD) → beide PreciousMetals-Engine.

    Fachliche Begründung: Basiswert (PRECIOUS_METAL) bestimmt die Analyse-Engine,
    nicht die Hülle (FUTURE vs. PHYSICAL_ETC). Beide Instrumente exponieren zum
    Goldpreis — beide brauchen die PM-Analyse (COT, Saisonalität, Zentralbank-Käufe).
    Die Unterschiede (Roll-Yield beim Future, Spread beim ETC) sind Phase-2-Schicht.
    """
    orch = _orchestrator_mit_gemockten_chiefs()
    asyncio.run(
        orch.run("GC", underlying=Underlying.PRECIOUS_METAL, wrapper=Wrapper.FUTURE)
    )
    asyncio.run(
        orch.run("GLD", underlying=Underlying.PRECIOUS_METAL, wrapper=Wrapper.PHYSICAL_ETC)
    )
    # Beide Aufrufe → PM-Engine; await_count == 2
    assert orch.precious_metals_chief.run.await_count == 2
    # Equity-Engine wurde kein einziges Mal aufgerufen
    orch.equity_chief.run.assert_not_awaited()
