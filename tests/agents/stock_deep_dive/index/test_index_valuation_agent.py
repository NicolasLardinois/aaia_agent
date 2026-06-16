import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.index.index_valuation_agent import IndexValuationAgent, _signal
from core.domain.models import Signal


def _agent(info: dict) -> IndexValuationAgent:
    market = MagicMock()
    market.get_info.return_value = info
    return IndexValuationAgent(market, MagicMock())


def test_signal_buffers_are_symmetric():
    # Bei _PE_RANGES["^GSPC"] = (15, 25): symmetrischer Puffer p.
    # Test: gleich weit unter low wie über high -> spiegelbildliches Signal.
    lo, hi = 15.0, 25.0
    p = 0.10
    assert _signal(lo * (1 - p) - 0.01, "^GSPC") == Signal.BULLISH
    assert _signal(hi * (1 + p) + 0.01, "^GSPC") == Signal.BEARISH
    # innerhalb der Range -> NEUTRAL
    assert _signal((lo + hi) / 2, "^GSPC") == Signal.NEUTRAL


def test_shiller_cape_is_filled_from_10y_real_eps():
    info = {
        "trailingPE": 20.0, "forwardPE": 18.0, "dividendYield": 0.018,
        "enterpriseToEbitda": 14.0,
        "regularMarketPrice": 4000.0,
        "eps10yReal": [180, 190, 200, 210, 220, 200, 200, 200, 200, 200],
    }
    result = asyncio.run(_agent(info).run("^GSPC"))
    # CAPE = 4000 / mean(...) = 4000 / 200 = 20.0
    assert result.shiller_cape == 20.0


def test_erp_signal_rate_dependent_low_erp_is_bearish():
    # PE 25 -> E/P 0.04; riskfree 0.045 -> ERP negativ -> teuer/BEARISH
    info = {"trailingPE": 25.0, "riskFreeRate": 0.045}
    result = asyncio.run(_agent(info).run("^GSPC"))
    assert result.signal == Signal.BEARISH


def test_erp_signal_rate_dependent_high_erp_is_bullish():
    # PE 12 -> E/P 0.0833; riskfree 0.02 -> ERP ~0.063 -> günstig/BULLISH
    info = {"trailingPE": 12.0, "riskFreeRate": 0.02}
    result = asyncio.run(_agent(info).run("^GSPC"))
    assert result.signal == Signal.BULLISH


def test_pe_zero_handled_via_is_not_none():
    info = {"trailingPE": 0.0, "regularMarketPrice": 4000.0}
    result = asyncio.run(_agent(info).run("^GSPC"))
    # 0.0 darf nicht zu None kollabieren (is not None), aber E/P undefiniert -> kein Crash.
    assert result is not None
