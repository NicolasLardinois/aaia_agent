"""Tests: BottomUpAnomalyAgent setzt direction aus Anomalie-Tendenz."""
from unittest.mock import MagicMock

import pytest

from agents.anomaly.bottom_up_anomaly_agent import BottomUpAnomalyAgent
from core.domain.models import Signal
from core.domain.taxonomy import legacy_to_taxonomy


def _make_bottom_up(
    pe=22.0,
    short_float=3.0,
    insider_tx=2,
    net_direction="neutral",
    fund_signal=Signal.BULLISH,
    val_signal=Signal.BULLISH,
    earn_signal=Signal.BULLISH,
    quality_signal=Signal.BULLISH,
    asset_class="equity",
):
    bu = MagicMock()
    # Task 8: underlying/wrapper statt asset_class-Property setzen.
    bu.underlying, bu.wrapper = legacy_to_taxonomy(asset_class)
    bu.fundamentals.pe_ratio = pe
    bu.fundamentals.signal = fund_signal
    bu.short_interest.short_float_pct = short_float
    bu.short_interest.signal = Signal.NEUTRAL
    bu.insider.recent_transactions = insider_tx
    bu.insider.net_direction = net_direction
    bu.insider.signal = Signal.NEUTRAL
    bu.earnings_trend.signal = earn_signal
    bu.moat.signal = Signal.NEUTRAL
    bu.valuation_range.signal = val_signal
    bu.quality.signal = quality_signal
    return bu


# ── Test 1: bearish — Short-Float deutlich erhöht ──────────────────────────
def test_direction_bearish_high_short_float():
    """Short-Float-Anomalie (hoch) → direction == 'bearish'."""
    agent = BottomUpAnomalyAgent()
    # Ruhige History: short_float_pct stabil bei ~3.0
    history = [
        {"indicators_snapshot": {"short_float_pct": 3.0 + (i % 3) * 0.1}}
        for i in range(25)
    ]
    # Aktueller Wert weit über der History
    bu = _make_bottom_up(short_float=35.0)
    report = agent.run(bu, history)
    assert any("Short-Float" in s for s in report.statistical), (
        "Kein Short-Float-Flag gefunden – Anomalie wurde nicht erkannt"
    )
    assert report.direction == "bearish", (
        f"Erwartet 'bearish', bekommen '{report.direction}'"
    )


# ── Test 2: bullish — Insider-Kauf-Cluster ────────────────────────────────
def test_direction_bullish_insider_buy_cluster():
    """Insider-Kauf-Cluster-Anomalie → direction == 'bullish'."""
    agent = BottomUpAnomalyAgent()
    # Ruhige History: nur 2–3 Insider-Transaktionen
    history = [
        {"indicators_snapshot": {"insider_transactions": 2}}
        for _ in range(25)
    ]
    bu = _make_bottom_up(insider_tx=40, net_direction="net_buy")
    report = agent.run(bu, history)
    assert any("Insider" in s for s in report.statistical), (
        "Kein Insider-Flag gefunden – Anomalie wurde nicht erkannt"
    )
    assert report.direction == "bullish", (
        f"Erwartet 'bullish', bekommen '{report.direction}'"
    )


# ── Test 3: neutral — keine History, keine Anomalie ───────────────────────
def test_direction_neutral_no_anomaly():
    """Keine History → kein Z-Score-Check → direction == 'neutral'."""
    agent = BottomUpAnomalyAgent()
    bu = _make_bottom_up()
    report = agent.run(bu, [])
    assert report.direction == "neutral", (
        f"Erwartet 'neutral', bekommen '{report.direction}'"
    )
