"""Regressions-Test zu Bug #1 (Audit 2026-06-20, §6 Logbuch).

Der ursprüngliche Crash: `load_bottom_up()` rekonstruierte den `BottomUpResult`
ohne die Felder `index` und `commodity_deep` → `TypeError`, sobald eine frische
Bottom-Up-Cache-Datei existierte (normaler Happy Path). Der Fix liest beide
Felder heute via `_load_index_result(...)` / `_load_commodity_deep(...)`.

Der bestehende Round-Trip-Test (`test_taxonomy_model_roundtrip.py`) prüft nur
`underlying`/`wrapper` und lässt `index`/`commodity_deep` auf `None` — die
eigentlich Bug-#1-auslösenden Felder bleiben dort ungetestet. Dieser Test
schliesst die Lücke: ein vollständig befüllter `index`/`commodity_deep` muss den
Disk-Round-Trip (save → JSON → load) feldgenau überleben.
"""
from core.domain.taxonomy import Underlying, Wrapper
from core.domain.models import (
    BottomUpResult, Signal,
    IndexResult, IndexPriceSnapshot, IndexValuationSnapshot,
    IndexEarningsSnapshot, IndexBreadthSnapshot, IndexMomentumSnapshot,
    SectorCompositionSnapshot, IndexValuationRangeSnapshot,
    CommodityBottomUpResult, SupplyDemandSnapshot, SeasonalitySnapshot,
    COTSnapshot, CommodityValuationRangeSnapshot,
)


def _index_result(ticker: str = "SPY") -> IndexResult:
    return IndexResult(
        ticker=ticker,
        price=IndexPriceSnapshot(
            current_price=500.0, perf_1w=0.01, perf_1m=0.02, perf_3m=0.03,
            perf_ytd=0.10, perf_1y=0.15, perf_3y=0.40, perf_5y=0.80,
            high_52w=520.0, low_52w=420.0, signal=Signal.BULLISH,
        ),
        valuation=IndexValuationSnapshot(
            pe_trailing=24.0, pe_forward=21.0, shiller_cape=33.0,
            dividend_yield=0.013, ev_ebitda=15.0, signal=Signal.BEARISH,
        ),
        earnings=IndexEarningsSnapshot(
            eps_growth_1y=0.08, revenue_growth_1y=0.05, operating_margin=0.18,
            estimate_revision="up", signal=Signal.BULLISH,
        ),
        breadth=IndexBreadthSnapshot(
            pct_above_ma50=0.62, pct_above_ma200=0.55, advance_decline_ratio=1.2,
            new_highs=120, new_lows=30, signal=Signal.NEUTRAL,
        ),
        momentum=IndexMomentumSnapshot(
            rsi_14=58.0, ma50=490.0, ma200=460.0, golden_cross=True,
            relative_strength=0.04, signal=Signal.BULLISH,
        ),
        composition=SectorCompositionSnapshot(
            top_sector="Technology", top_sector_weight=0.30, top_holding="AAPL",
            top_holding_weight=0.07, top_10_concentration=0.34, signal=Signal.NEUTRAL,
        ),
        valuation_range=IndexValuationRangeSnapshot(
            eps_estimate=22.0, pe_historical_low=16.0, pe_historical_high=26.0,
            price_low=352.0, price_mid=462.0, price_high=572.0, current_price=500.0,
            position="fair", signal=Signal.NEUTRAL,
        ),
    )


def _commodity_deep(commodity: str = "CL") -> CommodityBottomUpResult:
    return CommodityBottomUpResult(
        commodity=commodity,
        supply_demand=SupplyDemandSnapshot(
            inventory_current=420.0, inventory_avg_5y=460.0, inventory_pct_vs_avg=-0.087,
            production_change_yoy=0.02, stock_to_flow=0.15, stock_to_flow_signal="scarce",
            signal=Signal.BULLISH,
        ),
        seasonality=SeasonalitySnapshot(
            current_month_bias="bullish", avg_return_this_month=0.03,
            positive_years_pct=0.65, signal=Signal.BULLISH,
        ),
        cot=COTSnapshot(
            net_speculative_long=250000.0, net_speculative_pct_oi=0.18, signal=Signal.BEARISH,
        ),
        valuation_range=CommodityValuationRangeSnapshot(
            current_price=78.0, price_low_5y=20.0, price_high_5y=120.0,
            percentile_5y=0.58, percentile_10y=0.50, production_cost_low=45.0,
            production_cost_high=60.0, position="fair", signal=Signal.NEUTRAL,
        ),
        overall_signal=Signal.BULLISH,
        confidence=0.42,
    )


def _bottom_up_with_index_and_commodity() -> BottomUpResult:
    """Bug-#1-Konstellation: index UND commodity_deep befüllt (die zuvor verlorenen Felder)."""
    return BottomUpResult(
        ticker="SPY", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.FUND,
        fundamentals=None, quality=None, short_interest=None, insider=None,
        earnings_trend=None, moat=None, valuation_range=None,
        precious_metals=None, bond=None,
        index=_index_result("SPY"),
        commodity_deep=_commodity_deep("CL"),
    )


def _patch_cache(tmp_path, monkeypatch):
    """Cache-Datei auf tmp_path umbiegen + Freshness erzwingen (kein MAX_AGE-Problem)."""
    import adapters.cache.result_cache as rc_module
    monkeypatch.setattr(rc_module, "BOTTOMUP_FILE", str(tmp_path / "bottomup_{ticker}.json"))
    monkeypatch.setattr(rc_module, "_is_fresh", lambda path: True)
    from adapters.cache.result_cache import ResultCache
    return ResultCache()


def test_roundtrip_erhaelt_index_und_commodity_deep(tmp_path, monkeypatch):
    """Bug #1: index/commodity_deep dürfen den Disk-Round-Trip nicht verlieren."""
    cache = _patch_cache(tmp_path, monkeypatch)
    cache.save_bottom_up(_bottom_up_with_index_and_commodity())
    loaded = cache.load_bottom_up("SPY")

    # Kern der Regression: beide Felder kommen befüllt zurück (nicht None) — sonst
    # hätte der alte Loader sie gar nicht erst übergeben (→ TypeError).
    assert loaded.index is not None
    assert loaded.commodity_deep is not None

    # Stichproben über die verschachtelten Sub-Snapshots: Werte bleiben erhalten.
    assert loaded.index.ticker == "SPY"
    assert loaded.index.price.current_price == 500.0
    assert loaded.index.price.signal == Signal.BULLISH
    assert loaded.index.valuation.shiller_cape == 33.0
    assert loaded.index.momentum.golden_cross is True
    assert loaded.index.composition.top_sector == "Technology"

    assert loaded.commodity_deep.commodity == "CL"
    assert loaded.commodity_deep.supply_demand.stock_to_flow_signal == "scarce"
    assert loaded.commodity_deep.cot.signal == Signal.BEARISH
    assert loaded.commodity_deep.overall_signal == Signal.BULLISH
    assert loaded.commodity_deep.confidence == 0.42


def test_roundtrip_index_und_commodity_deep_none_bleiben_none(tmp_path, monkeypatch):
    """Gegenprobe: leere Optionalfelder bleiben sauber None (kein erfundenes Default-Objekt)."""
    cache = _patch_cache(tmp_path, monkeypatch)
    empty = BottomUpResult(
        ticker="AAPL", underlying=Underlying.EQUITY, wrapper=Wrapper.SINGLE,
        fundamentals=None, quality=None, short_interest=None, insider=None,
        earnings_trend=None, moat=None, valuation_range=None,
        precious_metals=None, bond=None, index=None, commodity_deep=None,
    )
    cache.save_bottom_up(empty)
    loaded = cache.load_bottom_up("AAPL")
    assert loaded.index is None
    assert loaded.commodity_deep is None
