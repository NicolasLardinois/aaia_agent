import asyncio

from core.domain.events import InsiderDataReady
from core.domain.models import InsiderSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = InsiderSnapshot(net_direction="neutral", recent_transactions=0, signal=Signal.NEUTRAL)

# Käufe signalstärker als Verkäufe (Verkäufe oft liquiditäts-/diversifikationsgetrieben).
_BUY_WEIGHT  = 1.5
_SELL_WEIGHT = 1.0
# Signal-Schwelle als Anteil des Netto- am Brutto-Volumen (Richtungs-Klarheit).
_NET_THRESHOLD = 0.20


def _is_informative(t: dict) -> bool:
    """Filtert geplante 10b5-1-Programme und Optionsausübungen heraus (nicht-informativ).
    Datenannahme: fehlende Felder → Transaktion gilt als open-market (informativ)."""
    if str(t.get("plan", "")).lower() in ("10b5-1", "10b5_1", "rule 10b5-1"):
        return False
    if t.get("acquisition_type") == "option_exercise":
        return False
    return True


def _magnitude(t: dict) -> float:
    """Wert (USD) bevorzugt, sonst Aktienzahl, sonst Einheitsgewicht 1.0."""
    val = t.get("value")
    if val is not None:
        return abs(float(val))
    shares = t.get("shares")
    if shares is not None:
        return abs(float(shares))
    return 1.0


def _net_value(transactions: list[dict]) -> float:
    """Wertgewichtete Netto-Insider-Aktivität (Käufe positiv, stärker gewichtet)."""
    net = 0.0
    for t in transactions:
        if not _is_informative(t):
            continue
        mag = _magnitude(t)
        if t.get("type") == "buy":
            net += _BUY_WEIGHT * mag
        elif t.get("type") == "sell":
            net -= _SELL_WEIGHT * mag
    return net


def _gross_value(transactions: list[dict]) -> float:
    total = 0.0
    for t in transactions:
        if not _is_informative(t):
            continue
        w = _BUY_WEIGHT if t.get("type") == "buy" else _SELL_WEIGHT
        total += w * _magnitude(t)
    return total


def _signal(net: float, total_abs: float) -> Signal:
    if total_abs <= 0.0:
        return Signal.NEUTRAL
    ratio = net / total_abs
    if ratio > _NET_THRESHOLD:
        return Signal.BULLISH
    if ratio < -_NET_THRESHOLD:
        return Signal.BEARISH
    return Signal.NEUTRAL


class InsiderAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> InsiderSnapshot:
        # Exception-Guard analog FundamentalsAgent: geworfener Fehler ODER als Wert
        # zurückgegebene Exception → leere Transaktionsliste (neutraler Default).
        try:
            transactions = await asyncio.to_thread(self.provider.get_insider_activity, ticker)
        except Exception:
            transactions = []
        if isinstance(transactions, Exception):
            transactions = []
        net   = _net_value(transactions)
        gross = _gross_value(transactions)
        signal = _signal(net, gross)
        direction = (
            "net_buy" if signal == Signal.BULLISH
            else "net_sell" if signal == Signal.BEARISH
            else "neutral"
        )
        result = InsiderSnapshot(net_direction=direction, recent_transactions=len(transactions), signal=signal)
        self.bus.publish(InsiderDataReady(source="insider_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> InsiderSnapshot:
        return _DEFAULT
