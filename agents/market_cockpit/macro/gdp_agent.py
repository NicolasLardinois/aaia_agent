import asyncio
from core.domain.events import GDPDataReady
from core.domain.models import GDPSnapshot, GDPDataPoint, Signal
from core.ports.data_provider import MacroDataProvider, EcbDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus

_NEUTRAL = GDPDataPoint(
    gdp_growth=None, industrial_production=None,
    unemployment=None, consumer_sentiment=None, pmi=None, signal=Signal.NEUTRAL,
)
_DEFAULT = GDPSnapshot(usa=_NEUTRAL, eurozone=_NEUTRAL, switzerland=_NEUTRAL)

# Länderspezifische Trend-BIP-Schwellen
_TREND_GDP = {"usa": 2.0, "eu": 1.2, "ch": 1.2}


def _sahm_recession(unemp_3m_avg: float | None, unemp_12m_low: float | None) -> bool | None:
    """Sahm-Regel: 3M-Durchschnitts-Arbeitslosenquote ≥0.5pp über 12M-Tief = Rezession."""
    if unemp_3m_avg is None or unemp_12m_low is None:
        return None
    return (unemp_3m_avg - unemp_12m_low) >= 0.5


def _sahm_from_history(history: list[float], min_months: int = 6) -> bool | None:
    """Sahm-Regel aus monatlicher Arbeitslosen-Historie (älteste zuerst):
    3M-Schnitt (jüngste 3 Monate) gegen 12M-Tief (Minimum der jüngsten 12 Monate).
    Unter `min_months` Beobachtungen → None — ein Rezessions-Call auf dünner Historie
    wäre verfrüht und fachlich nicht belastbar (kein Warm-up-Fehlsignal)."""
    if not history or len(history) < min_months:
        return None
    avg_3m = sum(history[-3:]) / 3
    low_12m = min(history[-12:])
    return _sahm_recession(avg_3m, low_12m)


def _signal(gdp_above_trend: bool | None, pmi: float | None, sahm: bool | None) -> Signal:
    """
    Score normiert auf die ANZAHL vorhandener Indikatoren (Durchschnitt statt fixer
    Summenschwelle). BIP relativ zum länderspezifischen Trendwachstum (gdp_above_trend),
    Arbeitslosigkeit über die Sahm-Regel (sahm) statt absoluter 5/8%-Schwellen.
    """
    if sahm is True:
        return Signal.BEARISH        # Sahm-Trigger dominiert (harter Rezessionsindikator)
    scores = []
    if gdp_above_trend is not None:
        scores.append(1 if gdp_above_trend else -1)
    if pmi is not None:
        scores.append(1 if pmi > 52 else (-1 if pmi < 48 else 0))
    if sahm is False:
        scores.append(1)             # keine Rezession laut Sahm = leicht positiv
    if not scores:
        return Signal.NEUTRAL
    avg = sum(scores) / len(scores)
    return Signal.BULLISH if avg >= 0.5 else (Signal.BEARISH if avg <= -0.5 else Signal.NEUTRAL)


class GDPAgent:
    def __init__(self, macro: MacroDataProvider, ecb: EcbDataProvider, snb: SnbDataProvider, bus: EventBus):
        self.macro = macro
        self.ecb   = ecb
        self.snb   = snb
        self.bus   = bus

    async def run(self) -> GDPSnapshot:
        state, ecb_gdp, ecb_unemp, ecb_unemp_hist, ecb_pmi, snb_gdp, snb_unemp = await asyncio.gather(
            asyncio.to_thread(self.macro.get_economic_state),
            asyncio.to_thread(self.ecb.get_gdp_growth),
            asyncio.to_thread(self.ecb.get_unemployment),
            asyncio.to_thread(self.ecb.get_unemployment_history),
            asyncio.to_thread(self.ecb.get_pmi),
            asyncio.to_thread(self.snb.get_gdp_growth),
            asyncio.to_thread(self.snb.get_unemployment),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v

        state          = _safe(state) or {}
        ecb_gdp        = _safe(ecb_gdp)
        ecb_unemp      = _safe(ecb_unemp)
        ecb_unemp_hist = _safe(ecb_unemp_hist) or []
        ecb_pmi        = _safe(ecb_pmi)
        snb_gdp        = _safe(snb_gdp)
        snb_unemp      = _safe(snb_unemp)

        usa_gdp   = state.get("gdp_growth")
        usa_unemp = state.get("unemployment")
        usa_above = (usa_gdp > _TREND_GDP["usa"]) if usa_gdp is not None else None
        # Sahm-Regel: 3M-Schnitt / 12M-Tief aus Historia nicht verfügbar → None
        usa_sahm  = _sahm_recession(None, None)

        usa = GDPDataPoint(
            gdp_growth=usa_gdp,
            industrial_production=state.get("industrial_production"),
            unemployment=usa_unemp,
            consumer_sentiment=state.get("consumer_sentiment"),
            pmi=None,   # TODO: ISM Manufacturing via FRED/ISM
            signal=_signal(usa_above, None, usa_sahm),
        )
        eu_above = (ecb_gdp > _TREND_GDP["eu"]) if ecb_gdp is not None else None
        # Sahm-Regel aus der monatlichen Eurostat-Arbeitslosen-Historie (EA21);
        # leere Historie → None → unverändertes Verhalten.
        eu_sahm = _sahm_from_history(ecb_unemp_hist)
        eu = GDPDataPoint(
            gdp_growth=ecb_gdp, industrial_production=None,
            unemployment=ecb_unemp, consumer_sentiment=None,
            pmi=ecb_pmi,
            signal=_signal(eu_above, ecb_pmi, eu_sahm),
        )
        ch_above = (snb_gdp > _TREND_GDP["ch"]) if snb_gdp is not None else None
        ch = GDPDataPoint(
            gdp_growth=snb_gdp, industrial_production=None,
            unemployment=snb_unemp, consumer_sentiment=None,
            pmi=None,   # TODO: procure.ch PMI
            signal=_signal(ch_above, None, None),
        )
        result = GDPSnapshot(usa=usa, eurozone=eu, switzerland=ch)
        self.bus.publish(GDPDataReady(source="gdp_agent", payload={
            "usa_gdp": usa.gdp_growth, "eu_gdp": ecb_gdp, "ch_gdp": snb_gdp,
        }))
        return result

    @staticmethod
    def default() -> GDPSnapshot:
        return _DEFAULT
