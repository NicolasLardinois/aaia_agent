import asyncio
import logging
from core.domain.events import PreciousMetalsMacroDataReady
from core.domain.models import PreciousMetalsMacroSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.relative import percentile_rank, zscore_vs_history
from core.utils.safe import safe_result

_log = logging.getLogger(__name__)

TICKERS = {"gold": "GC=F", "silver": "SI=F", "platinum": "PL=F", "palladium": "PA=F"}

_DEFAULT = PreciousMetalsMacroSnapshot(
    gold_usd=None, silver_usd=None, platinum_usd=None, palladium_usd=None,
    gold_silver_ratio=None, gold_platinum_ratio=None, signal=Signal.NEUTRAL,
)

_GS_HIGH = 0.85
_GS_LOW  = 0.15
_GOLD_Z  = 1.5


def _signal(gs_pct: float | None, gold_z: float | None) -> Signal:
    """
    Edelmetall-Makro-Signal über RELATIVE Maße:
    - Gold/Silber-Ratio als Perzentil-Rang gegen die rollierende Historie
      (oberes Extrem = Risikoaversion → BEARISH; unteres = Risk-on → BULLISH).
    - Gold-Momentum-z (Safe-Haven-Nachfrage) als Override Richtung BEARISH.
    Keine fixen Absolut-Anker (80/50, 1.0) mehr.
    """
    if gold_z is not None and gold_z > _GOLD_Z:
        return Signal.BEARISH
    if gs_pct is None:
        return Signal.NEUTRAL
    if gs_pct >= _GS_HIGH:
        return Signal.BEARISH
    if gs_pct <= _GS_LOW:
        return Signal.BULLISH
    return Signal.NEUTRAL


def _gold_momentum_z(hist) -> float | None:
    """12M-Gold-Return als z-Score gegen die rollierende Return-Historie."""
    if hist is None or isinstance(hist, Exception):
        return None
    try:
        close = hist["Close"].dropna()
        if len(close) < 30:
            return None
        monthly = close.pct_change(21).dropna()
        if len(monthly) < 20:
            return None
        current = float((close.iloc[-1] - close.iloc[0]) / close.iloc[0])
        return zscore_vs_history(current, monthly.tolist(), robust=True, min_n=20)
    except Exception:
        return None


def _gs_ratio_percentile(gold_hist, silver_hist) -> float | None:
    """Aktuelles Gold/Silber-Ratio als Perzentil-Rang (0..1) gegen rollierende Historie."""
    if gold_hist is None or silver_hist is None:
        return None
    if isinstance(gold_hist, Exception) or isinstance(silver_hist, Exception):
        return None
    try:
        au = gold_hist["Close"].dropna()
        ag = silver_hist["Close"].dropna()
        ratio = (au / ag).dropna()
        if len(ratio) < 20:
            return None
        current = float(ratio.iloc[-1])
        history = ratio.tolist()
        pct = percentile_rank(current, history)
        if pct is None:
            return None
        return pct / 100.0   # normalize to 0..1
    except Exception:
        return None


class PreciousMetalsMacroAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> PreciousMetalsMacroSnapshot:
        (gold, silver, platinum, palladium), (h_gold, h_silver) = await asyncio.gather(
            asyncio.gather(
                asyncio.to_thread(self.provider.get_current_price, TICKERS["gold"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["silver"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["platinum"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["palladium"]),
                return_exceptions=True,
            ),
            asyncio.gather(
                asyncio.to_thread(self.provider.get_price_history, TICKERS["gold"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["silver"], "1y"),
                return_exceptions=True,
            ),
        )
        # Ausgefallene Preisquelle -> None (geteilter Helfer statt lokalem _safe).
        # label+logger: ein ausgefallener Metallpreis wird als warning sichtbar.
        gold = safe_result(gold, default=None, label=f"Precious Metals Macro Gold ({TICKERS['gold']})", logger=_log)
        silver = safe_result(silver, default=None, label=f"Precious Metals Macro Silver ({TICKERS['silver']})", logger=_log)
        platinum = safe_result(platinum, default=None, label=f"Precious Metals Macro Platinum ({TICKERS['platinum']})", logger=_log)
        palladium = safe_result(palladium, default=None, label=f"Precious Metals Macro Palladium ({TICKERS['palladium']})", logger=_log)

        gs_ratio = round(gold / silver, 2) if gold is not None and silver is not None and silver > 0 else None
        gp_ratio = round(gold / platinum, 2) if gold is not None and platinum is not None and platinum > 0 else None

        gs_pct  = _gs_ratio_percentile(h_gold, h_silver)
        gold_z  = _gold_momentum_z(h_gold)

        result = PreciousMetalsMacroSnapshot(
            gold_usd=gold, silver_usd=silver, platinum_usd=platinum, palladium_usd=palladium,
            gold_silver_ratio=gs_ratio, gold_platinum_ratio=gp_ratio,
            signal=_signal(gs_pct, gold_z),
        )
        self.bus.publish(PreciousMetalsMacroDataReady(source="precious_metals_macro_agent", payload={
            "gold": gold, "silver": silver, "gs_ratio": gs_ratio,
        }))
        return result

    @staticmethod
    def default() -> PreciousMetalsMacroSnapshot:
        return _DEFAULT
