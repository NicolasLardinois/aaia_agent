from core.domain.models import Signal, SignalStatus

_SCORE = {Signal.BULLISH: 1.0, Signal.BEARISH: -1.0, Signal.NEUTRAL: 0.0}
_THRESHOLD = 0.15


def weighted_signal(
    items: list[tuple[Signal, float, SignalStatus]],
) -> tuple[Signal, float]:
    """Gewichtetes Voting. UNAVAILABLE-Items ignorieren, Gewichte der
    verbleibenden re-normalisieren. Mapping BULLISH=+1, BEARISH=-1, NEUTRAL=0.
    net = Sum(w_i*s_i)/Sum(w_i) ueber AVAILABLE.
    Rueckgabe: (BULLISH wenn net>+0.15, BEARISH wenn net<-0.15, sonst NEUTRAL;
    confidence=min(1.0,abs(net)))."""
    available = [(sig, w) for sig, w, status in items if status == SignalStatus.AVAILABLE]
    weight_total = sum(w for _, w in available)
    if weight_total <= 0.0:
        return Signal.NEUTRAL, 0.0

    net = sum(_SCORE[sig] * w for sig, w in available) / weight_total
    confidence = min(1.0, abs(net))

    if net > _THRESHOLD:
        return Signal.BULLISH, confidence
    if net < -_THRESHOLD:
        return Signal.BEARISH, confidence
    return Signal.NEUTRAL, confidence
