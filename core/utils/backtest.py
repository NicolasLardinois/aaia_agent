import math
from datetime import datetime
from typing import Callable, Optional

HORIZONS_DAYS: tuple[int, ...] = (30, 60, 90)
MIN_SAMPLE: int = 10

_EUROZONE = {
    "DE", "FR", "IT", "ES", "NL", "AT", "BE", "PT", "FI", "IE",
    "GR", "SK", "SI", "EE", "LV", "LT", "LU", "MT", "CY",
}
BENCHMARK_BY_MARKET: dict[str, str] = {"USA": "^GSPC", "CH": "^SSMI"}
_DEFAULT_BENCHMARK = "^GSPC"

# Mapping Signal/Empfehlung → erwartete Richtung des marktbereinigten Returns.
# HOLD/neutral sind KEINE Richtungswetten und können nie "correct" sein.
_BULLISH = {"bullish", "buy"}
_BEARISH = {"bearish", "sell", "short"}


def benchmark_for_market(market: str) -> str:
    m = (market or "").upper().strip()
    if m in BENCHMARK_BY_MARKET:
        return BENCHMARK_BY_MARKET[m]
    if m in _EUROZONE:
        return "^STOXX"
    return _DEFAULT_BENCHMARK


def forward_return(price_entry: float, price_forward: Optional[float]) -> Optional[float]:
    """Forward-Return über fixes Window. price_forward=None → Totalverlust (Survivorship-Fix)."""
    if price_entry is None or price_entry <= 0:
        return None
    if price_forward is None:
        return -1.0
    return (price_forward - price_entry) / price_entry


def market_adjusted_return(asset_ret: float, benchmark_ret: Optional[float]) -> float:
    """Alpha = Asset-Return − Benchmark-Return. Kein Benchmark → roher Return."""
    if benchmark_ret is None:
        return asset_ret
    return asset_ret - benchmark_ret


def is_correct(action: str, adjusted_return: float) -> bool:
    """Korrekt = marktbereinigtes Vorzeichen passt zur Richtung. Keine 'neutral'-Klasse."""
    a = (action or "").strip().lower()
    if a in _BULLISH:
        return adjusted_return > 0
    if a in _BEARISH:
        return adjusted_return < 0
    return False


def no_price_on_horizon(ticker: str, entry_date: datetime, horizon_days: int) -> Optional[float]:
    """Defensiver No-Op-Default ohne injizierte Kursquelle: kein Kurs → None (kein I/O).

    Verhaltens-identisch zum bisherigen geblockten-Netz-Pfad: ohne echte Quelle
    liefern die Backtester keine Forward-Kurse und überspringen die Bewertung,
    statt zu raten oder abzustürzen.
    """
    return None


def make_benchmark_return(
    price_on_horizon: Callable[[str, datetime, int], Optional[float]],
) -> Callable[[str, datetime, int], Optional[float]]:
    """Baut die benchmark_return-Funktion aus einer Kurs-Lookup-Funktion.

    Reine Ableitung (Benchmark-Ticker je Markt → Forward-Return des Benchmarks);
    das einzige I/O steckt im injizierten ``price_on_horizon``. So bleibt die
    Geschäftslogik (Markt→Benchmark, Forward-Return) im Kern, das Netz im Adapter.
    """
    def _benchmark_return(market: str, entry_date: datetime, horizon_days: int) -> Optional[float]:
        bench = benchmark_for_market(market)
        entry_px = price_on_horizon(bench, entry_date, 0)
        fwd_px = price_on_horizon(bench, entry_date, horizon_days)
        return forward_return(entry_px, fwd_px) if entry_px else None
    return _benchmark_return


# Defensiver Benchmark-Default ohne Quelle: liefert immer None (kein Netz).
no_benchmark_return: Callable[[str, datetime, int], Optional[float]] = make_benchmark_return(
    no_price_on_horizon
)


def hit_rate_ci(correct: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson-Score-Konfidenzintervall der Trefferrate. total=0 → (0.0, 0.0)."""
    if total <= 0:
        return (0.0, 0.0)
    p = correct / total
    denom = 1.0 + z ** 2 / total
    center = (p + z ** 2 / (2 * total)) / denom
    margin = (z * math.sqrt(p * (1 - p) / total + z ** 2 / (4 * total ** 2))) / denom
    lo = max(0.0, center - margin)
    hi = min(1.0, center + margin)
    return (round(lo, 4), round(hi, 4))
