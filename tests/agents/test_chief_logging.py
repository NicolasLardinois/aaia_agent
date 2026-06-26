"""Logging-Pass 3/3 — Chief-/Orchestrator-Aufrufstellen.

Auf Chief-/Orchestrator-Ebene entpackt `safe_result(...)` nicht eine einzelne
Datenquelle, sondern das Ergebnis eines *ganzen* Sub-Agenten (bzw. Sub-Chiefs).
Faellt ein Sub-Agent komplett aus (Exception), soll das jetzt als `warning`
sichtbar werden — mit einem `label`, das den ausgefallenen Sub-Agenten benennt
(z. B. ``"MacroChief: InflationAgent"``). Das Analyse-Verhalten bleibt identisch:
der Default des Sub-Agenten greift weiter, nur eben nicht mehr stillschweigend.

Test-Strategie: Jeden Chief mit MagicMock-Providern bauen (Signatur-Introspektion),
*alle* Sub-Agenten zum Werfen bringen — dann laeuft der Chief vollstaendig auf
Defaults (der gut getestete „alle Quellen aus"-Pfad) und loggt fuer jeden
ausgefallenen Sub-Agenten genau ein `warning`. Geprueft wird je Datei, dass das
erwartete Label im Log auftaucht.
"""
import asyncio
import inspect
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.domain.models import MarketRegime, RiskAffinity

from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.stock_deep_dive.equity_chief_agent import EquityChiefAgent
from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent
from agents.stock_deep_dive.index_chief_agent import IndexChiefAgent
from agents.stock_deep_dive.precious_metals_chief_agent import PreciousMetalsChiefAgent
from agents.stock_deep_dive.commodity_chief_agent_mikro import CommodityChiefAgentMikro
from orchestrators.top_down_orchestrator import TopDownOrchestrator


def _build(cls):
    """Konstruiert einen Chief/Orchestrator mit MagicMock fuer jeden __init__-Parameter.

    Der genaue Provider-Typ ist fuer den Logging-Pfad egal — wir ueberschreiben
    ohnehin gleich jeden Sub-Agenten. So muss der Test keine 11 Konstruktoren von
    Hand nachbauen und bricht nicht, wenn sich eine Signatur leicht aendert.
    """
    sig = inspect.signature(cls.__init__)
    kwargs = {name: MagicMock() for name in sig.parameters if name != "self"}
    return cls(**kwargs)


def _break_all_subagents(chief):
    """Bringt jeden Sub-Agenten/Sub-Chief zum Werfen (run -> RuntimeError).

    Erkennung ueber `asyncio.iscoroutinefunction(attr.run)`: trifft echte
    Agent-/Chief-Instanzen, nicht die MagicMock-Provider (deren `.run` ist ein
    MagicMock, keine Koroutine). Damit landet der Chief auf dem reinen Default-Pfad.
    """
    for value in vars(chief).values():
        run = getattr(value, "run", None)
        if run is not None and asyncio.iscoroutinefunction(run):
            value.run = AsyncMock(side_effect=RuntimeError("Quelle ausgefallen"))


# (Klasse, run-Argumente, erwartetes Label-Fragment eines ausgefallenen Sub-Agenten)
_CASES = [
    (MacroChiefAgent,            (),                                                "MacroChief: InflationAgent"),
    (SentimentChiefAgent,        (),                                                "SentimentChief: VIXAgent"),
    (YieldCurveChiefAgent,       (),                                                "YieldCurveChief: YieldSpreadAgent"),
    (SectorChiefAgent,           (MarketRegime.EXPANSION,),                         "SectorChief: SectorPerformanceAgent"),
    (CommodityChiefAgentMakro,   (),                                                "CommodityChiefMakro: EnergyAgent"),
    (EquityChiefAgent,           ("AAPL",),                                         "EquityChief: FundamentalsAgent"),
    (BondChiefAgent,             ("XS1", "government", "stable", RiskAffinity.NEUTRAL), "BondChief: BondMetricsAgent"),
    (IndexChiefAgent,            ("SPY",),                                          "IndexChief: IndexPriceAgent"),
    (PreciousMetalsChiefAgent,   ("gold",),                                         "PreciousMetalsChief: PreciousMetalPriceAgent"),
    (CommodityChiefAgentMikro,   ("CL=F",),                                         "CommodityChiefMikro: SupplyDemandAgent"),
    (TopDownOrchestrator,        (),                                                "TopDownOrchestrator: MacroChiefAgent"),
]


@pytest.mark.parametrize("cls, run_args, expected_label", _CASES,
                         ids=[c[0].__name__ for c in _CASES])
def test_chief_loggt_warnung_bei_ausgefallenem_subagenten(cls, run_args, expected_label, caplog):
    chief = _build(cls)
    _break_all_subagents(chief)

    with caplog.at_level(logging.WARNING):
        result = asyncio.run(chief.run(*run_args))

    # Der Chief stuerzt nicht ab — er liefert trotz Ausfall ein Ergebnis (Default-Pfad).
    assert result is not None
    # ... und der Ausfall ist jetzt als benannte Warnung sichtbar (statt stillschweigend).
    assert expected_label in caplog.text
    assert "ausgefallen" in caplog.text.lower()
