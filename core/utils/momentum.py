"""Geteilte Momentum-Helfer für Equity- und Index-Momentum-Agenten.

Alle Funktionen sind rein (pure functions) ohne Seiteneffekte — kein I/O,
keine externen Abhängigkeiten ausserhalb von core/domain.
"""
import math
import pandas as pd

from core.domain.models import Signal


def momentum_signal(
    ma50,
    ma200,
    rsi,
    *,
    overbought: float = 70.0,
    oversold: float = 30.0,
) -> Signal:
    """Signal aus Trend-Status (MA50 vs MA200) kombiniert mit RSI-Extremen.

    Fachliche Logik:
    - MA50 > MA200 = Aufwärtstrend (Golden-Cross-Regime). Ist der RSI dabei
      nicht überkauft (< 70), bleibt Aufwärtsmomentum intakt → BULLISH.
    - Ist der RSI > 70 (überkauft), ist eine Korrektur wahrscheinlich → NEUTRAL
      statt BULLISH (kein Einstiegs-Signal bei extremem RSI).
    - MA50 < MA200 = Abwärtstrend. Ist RSI < 30 (überverkauft), droht eine
      technische Gegenbewegung → NEUTRAL (kein Short-Signal beim RSI-Boden).
    - Abwärtstrend ohne Überverkauf → BEARISH.
    - None oder NaN in den Eingaben (zu wenig Daten) → NEUTRAL.

    Args:
        ma50: 50-Tage-Gleitender Durchschnitt des Kurses (float oder None).
        ma200: 200-Tage-Gleitender Durchschnitt des Kurses (float oder None).
        rsi: 14-Tage-RSI (0–100). Darf None sein.
        overbought: RSI-Grenze für überkauft (Standard 70).
        oversold: RSI-Grenze für überverkauft (Standard 30).

    Returns:
        Signal.BULLISH | Signal.BEARISH | Signal.NEUTRAL
    """
    # Fehlende oder ungültige Eingaben → kein verwertbares Signal
    if ma50 is None or ma200 is None:
        return Signal.NEUTRAL
    if math.isnan(ma50) or math.isnan(ma200):
        return Signal.NEUTRAL

    if ma50 > ma200:
        # Aufwärtstrend — RSI-Überkauf dämpft Signal
        if rsi is not None and rsi > overbought:
            return Signal.NEUTRAL
        return Signal.BULLISH

    # Abwärtstrend — RSI-Überverkauf dämpft Signal (technische Erholung möglich)
    if rsi is not None and rsi < oversold:
        return Signal.NEUTRAL
    return Signal.BEARISH


def detect_crossover(
    ma50_series: pd.Series,
    ma200_series: pd.Series,
    window: int = 5,
) -> bool | None:
    """Erkennt Golden Cross (True) oder Death Cross (False) im letzten Fenster.

    Fachliche Logik:
    - Golden Cross: MA50 kreuzt MA200 von unten nach oben — klassisches
      Kaufsignal in der technischen Analyse (Aufwärtstrend etabliert sich).
    - Death Cross: MA50 kreuzt MA200 von oben nach unten — klassisches
      Verkaufssignal (Abwärtstrend etabliert sich).
    - Kein Kreuz im Fenster → None.

    Das Kreuz wird über Vorzeichenwechsel der Differenz MA50 − MA200 erkannt:
    Wechsel von negativ nach positiv = Golden Cross; umgekehrt = Death Cross.

    Args:
        ma50_series: Zeitreihe der MA50-Werte.
        ma200_series: Zeitreihe der MA200-Werte.
        window: Anzahl der letzten Datenpunkte, in denen ein Kreuz gesucht wird.

    Returns:
        True = Golden Cross, False = Death Cross, None = kein Kreuz im Fenster.
    """
    try:
        diff = ma50_series - ma200_series
        # Letztes Fenster + 1 Datenpunkt davor als Referenz
        recent = diff.iloc[-(window + 1):]
        if len(recent) < 2:
            return None
        was_above = recent.iloc[0] > 0
        is_above = recent.iloc[-1] > 0
        if not was_above and is_above:
            return True   # Golden Cross
        if was_above and not is_above:
            return False  # Death Cross
        return None       # Kein Kreuz im Fenster
    except Exception:
        return None
