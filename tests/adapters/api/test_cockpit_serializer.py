from core.domain.models import (
    CockpitResult, SignalStatus, Signal, MarketRegime,
    SentimentChiefResult, VIXSnapshot, FearGreedSnapshot, PutCallSnapshot,
    YieldCurveChiefResult, YieldSpreadSnapshot, YieldSpreadDataPoint, SovereignSpreadSnapshot,
    SectorChiefResult, SectorPerformanceSnapshot, SectorRotationSnapshot,
    CommodityChiefResult, EnergySnapshot, IndustrialMetalsSnapshot,
    PreciousMetalsMacroSnapshot, AgriculturalSnapshot,
    BuffettIndicatorSnapshot, BuffettCountryPoint,
)
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from adapters.api.cockpit_serializer import cockpit_to_dict


def _available_cockpit() -> CockpitResult:
    """Voll verfuegbares Cockpit mit eindeutigen Signalen pro Domaene."""
    macro = MacroChiefAgent.default()
    macro.regime = MarketRegime.EXPANSION
    macro.regime_confidence = 0.71
    macro.status = SignalStatus.AVAILABLE

    commodities = CommodityChiefResult(
        energy=EnergySnapshot(None, None, None, Signal.NEUTRAL),
        industrial_metals=IndustrialMetalsSnapshot(None, None, None, None, Signal.NEUTRAL),
        precious_metals=PreciousMetalsMacroSnapshot(None, None, None, None, None, None, Signal.NEUTRAL),
        agricultural=AgriculturalSnapshot(None, None, None, None, None, None, None, Signal.NEUTRAL),
        signal=Signal.NEUTRAL, status=SignalStatus.AVAILABLE,
    )
    sentiment = SentimentChiefResult(
        vix=VIXSnapshot(None, None, Signal.NEUTRAL),
        fear_greed=FearGreedSnapshot(None, "Neutral", Signal.NEUTRAL),
        put_call=PutCallSnapshot(None, Signal.NEUTRAL),
        signal=Signal.BEARISH, status=SignalStatus.AVAILABLE,
    )
    spread = YieldSpreadDataPoint(0.4, 1.1, 0.7, False, Signal.BULLISH)
    yield_curve = YieldCurveChiefResult(
        yield_spreads=YieldSpreadSnapshot(usa=spread, eurozone=spread, switzerland=spread),
        sovereign_spreads=SovereignSpreadSnapshot(None, None, None, Signal.NEUTRAL),
        signal=Signal.BULLISH, status=SignalStatus.AVAILABLE,
    )
    sectors = SectorChiefResult(
        performance=SectorPerformanceSnapshot(usa={}, eurozone={}, leading_usa="Tech", lagging_usa="Energy", leading_eu="", lagging_eu=""),
        rotation=SectorRotationSnapshot(recommended=[], avoid=[], alignment="neutral", signal=Signal.NEUTRAL),
        status=SignalStatus.AVAILABLE,
    )
    return CockpitResult(macro=macro, commodities=commodities, sentiment=sentiment, yield_curve=yield_curve, sectors=sectors)


def test_serializes_regime_and_domains_when_all_available():
    d = cockpit_to_dict(_available_cockpit())
    assert d["regime"] == "Aufschwung"          # MarketRegime.EXPANSION.value
    assert d["regime_confidence"] == 0.71
    assert d["macro_status"] == "available"
    keys = [e["key"] for e in d["domains"]]
    assert keys == ["commodities", "sentiment", "yield_curve", "sectors"]
    by_key = {e["key"]: e for e in d["domains"]}
    assert by_key["sentiment"]["signal"] == "bearish"
    assert by_key["yield_curve"]["signal"] == "bullish"
    assert by_key["sectors"]["signal"] == "neutral"   # aus rotation.signal
    assert d["sources_total"] == 5
    assert d["sources_active"] == 5


def test_unavailable_domain_is_excluded_from_active_and_marked():
    # Alle-Default-Cockpit => alle Chiefs UNAVAILABLE => 0/5 aktiv.
    result = CockpitResult(
        macro=MacroChiefAgent.default(),
        commodities=CommodityChiefAgentMakro.default(),
        sentiment=SentimentChiefAgent.default(),
        yield_curve=YieldCurveChiefAgent.default(),
        sectors=SectorChiefAgent.default(),
    )
    d = cockpit_to_dict(result)
    assert d["macro_status"] == "unavailable"
    assert all(e["status"] == "unavailable" for e in d["domains"])
    assert d["sources_active"] == 0
    assert d["sources_total"] == 5


def test_partial_availability_excludes_only_the_unavailable_domain():
    # Mischzustand: eine Domaene faellt aus -> sie zaehlt NICHT in sources_active,
    # die uebrigen schon. Faengt ein Off-by-One in der Zaehllogik ab, das die
    # beiden Extrem-Tests (alle/keine verfuegbar) nicht falsifizieren koennten.
    result = _available_cockpit()
    result.commodities.status = SignalStatus.UNAVAILABLE
    d = cockpit_to_dict(result)
    by_key = {e["key"]: e for e in d["domains"]}
    assert by_key["commodities"]["status"] == "unavailable"
    assert by_key["sentiment"]["status"] == "available"
    assert d["sources_total"] == 5
    assert d["sources_active"] == 4   # Macro + 3 Sub-Domaenen verfuegbar


def test_unavailable_domain_signal_is_null_not_neutral():
    # AGENTS.md §3 / Spec §6: UNAVAILABLE ≠ NEUTRAL. Eine ausgefallene Domaene
    # traegt im Default Signal.NEUTRAL — die API darf das NICHT als echtes
    # "neutral" ausliefern (sonst sieht ein Consumer ein erfundenes Signal fuer
    # eine Quelle ohne Daten). Bei status=unavailable muss signal None sein.
    result = _available_cockpit()
    result.commodities.status = SignalStatus.UNAVAILABLE
    d = cockpit_to_dict(result)
    by_key = {e["key"]: e for e in d["domains"]}
    assert by_key["commodities"]["signal"] is None        # nicht "neutral"
    assert by_key["commodities"]["status"] == "unavailable"
    # Verfuegbare Domaene traegt weiterhin ihr echtes Signal.
    assert by_key["sentiment"]["signal"] == "bearish"


def test_all_unavailable_domains_have_null_signal():
    # Alle-Default-Cockpit => jede Sub-Domaene unavailable => signal ueberall None.
    result = CockpitResult(
        macro=MacroChiefAgent.default(),
        commodities=CommodityChiefAgentMakro.default(),
        sentiment=SentimentChiefAgent.default(),
        yield_curve=YieldCurveChiefAgent.default(),
        sectors=SectorChiefAgent.default(),
    )
    d = cockpit_to_dict(result)
    assert all(e["signal"] is None for e in d["domains"])


# ─────────────────────────────────────────────
# Drilldown-Detail: Buffett-Indikator (US5/US6)
# Der Cockpit-Lauf berechnet die Buffett-Daten (Weltbank + FRED) bereits voll —
# der Serializer reicht sie jetzt unter detail.buffett an das Frontend durch.
# Schluessel snake_case (API-Konvention wie regime_confidence/sources_active);
# das Frontend mappt auf seinen camelCase-Vertrag (BuffettView).
# ─────────────────────────────────────────────

def _buffett_snapshot() -> BuffettIndicatorSnapshot:
    """Zwei Laender mit unterschiedlichem Pfad: USA (FRED, Echtzeit -> year=None)
    und CHE (Weltbank-Jahreswert -> year gesetzt)."""
    return BuffettIndicatorSnapshot(
        countries={
            "USA": BuffettCountryPoint(ratio_pct=200.0, signal=Signal.BEARISH, year=None, z_score=1.6,
                                       name="United States"),
            "CHE": BuffettCountryPoint(ratio_pct=230.0, signal=Signal.NEUTRAL, year=2023, z_score=0.3,
                                       name="Switzerland"),
        },
        signal=Signal.BEARISH,
        global_median=95.4,
    )


def test_detail_buffett_serializes_countries_and_global_median():
    cockpit = _available_cockpit()
    cockpit.macro.buffett_indicator = _buffett_snapshot()
    d = cockpit_to_dict(cockpit)

    buffett = d["detail"]["buffett"]
    assert buffett["global_median"] == 95.4

    by_iso = {c["iso3"]: c for c in buffett["countries"]}
    assert by_iso["USA"]["ratio_pct"] == 200.0
    assert by_iso["USA"]["name"] == "United States"  # Ländername (Weltbank/FRED)
    assert by_iso["USA"]["signal"] == "bearish"   # echtes Signal, kein None
    assert by_iso["USA"]["z_score"] == 1.6
    assert by_iso["USA"]["year"] is None          # Echtzeit (FRED)
    assert by_iso["CHE"]["year"] == 2023          # Weltbank-Jahreswert
    assert by_iso["CHE"]["name"] == "Switzerland"
    assert by_iso["CHE"]["signal"] == "neutral"


def test_detail_buffett_includes_per_country_history():
    # Der Einzelland-Drilldown zeigt die 10-J-Historie der Ratio. Die Weltbank-Serie
    # wird ohnehin fuer den z-Score geholt -> hier nur durchgereicht (year aufsteigend).
    cockpit = _available_cockpit()
    cockpit.macro.buffett_indicator = BuffettIndicatorSnapshot(
        countries={
            "CHE": BuffettCountryPoint(
                ratio_pct=230.0, signal=Signal.NEUTRAL, year=2023, z_score=0.3,
                history=[(2021, 210.0), (2022, 225.0), (2023, 230.0)],
            ),
            "USA": BuffettCountryPoint(ratio_pct=200.0, signal=Signal.BEARISH, year=None, z_score=1.6),
        },
        signal=Signal.BEARISH, global_median=95.4,
    )
    d = cockpit_to_dict(cockpit)

    by_iso = {c["iso3"]: c for c in d["detail"]["buffett"]["countries"]}
    assert by_iso["CHE"]["history"] == [
        {"year": 2021, "ratio_pct": 210.0},
        {"year": 2022, "ratio_pct": 225.0},
        {"year": 2023, "ratio_pct": 230.0},
    ]
    assert by_iso["USA"]["history"] == []   # ohne Historie -> leere Liste, nicht fehlend
