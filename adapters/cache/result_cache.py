import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

CACHE_DIR     = os.path.join(os.path.dirname(__file__), "..", "..", ".cache")
COCKPIT_FILE  = os.path.join(CACHE_DIR, "cockpit.json")
BOTTOMUP_FILE = os.path.join(CACHE_DIR, "bottomup_{ticker}.json")
MAX_AGE       = timedelta(hours=1)

os.makedirs(CACHE_DIR, exist_ok=True)


def _is_fresh(path: str) -> bool:
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    saved_at = datetime.fromisoformat(data.get("_saved_at", "2000-01-01"))
    # Rueckwaertskompatibel: alte Cache-Dateien tragen einen naiven _saved_at
    # (ohne Zeitzone). Als UTC interpretieren, damit der Vergleich gegen das
    # tz-aware now() nicht am "naiv - aware"-TypeError scheitert.
    if saved_at.tzinfo is None:
        saved_at = saved_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - saved_at < MAX_AGE


# ─── Serialize helpers ────────────────────────────────────────────────────────

def _sv(signal) -> Optional[str]:
    """Signal → string value, or None."""
    return signal.value if signal is not None else None


def _moat_score_out(ms) -> Optional[dict]:
    if ms is None:
        return None
    return {"score": ms.score, "evidence": ms.evidence}


def _valuation_method_out(vm) -> dict:
    return {"name": vm.name, "low": vm.low, "high": vm.high, "currency": vm.currency}


def _valuation_range_out(vr) -> Optional[dict]:
    if vr is None:
        return None
    return {
        "methods":       [_valuation_method_out(m) for m in vr.methods],
        "combined_low":  vr.combined_low,
        "combined_high": vr.combined_high,
        "current_price": vr.current_price,
        "position":      vr.position,
        "signal":        _sv(vr.signal),
    }


def _precious_metal_snapshot_out(ps) -> Optional[dict]:
    if ps is None:
        return None
    return {
        "metal":                    ps.metal,
        "price_usd":                ps.price_usd,
        "performance":              ps.performance,
        "rsi":                      ps.rsi,
        "ma50":                     ps.ma50,
        "ma200":                    ps.ma200,
        "stock_to_flow":            ps.stock_to_flow,
        "real_yield_correlation":   ps.real_yield_correlation,
        "signal":                   _sv(ps.signal),
    }


def _cross_metal_out(cm) -> Optional[dict]:
    if cm is None:
        return None
    return {
        "gold_silver_ratio":   cm.gold_silver_ratio,
        "gold_platinum_ratio": cm.gold_platinum_ratio,
        "signal":              _sv(cm.signal),
    }


def _precious_metals_result_out(pm) -> Optional[dict]:
    if pm is None:
        return None
    return {
        "metal":           pm.metal,
        "price_analysis":  _precious_metal_snapshot_out(pm.price_analysis),
        "cross_metal":     _cross_metal_out(pm.cross_metal),
        "valuation_range": _valuation_range_out(pm.valuation_range),
        "cot_signal":      _sv(pm.cot_signal),
        "currency_impact": pm.currency_impact,
    }


def _bond_metrics_out(bm) -> Optional[dict]:
    if bm is None:
        return None
    return {
        "bond_type":            bm.bond_type,
        "current_price":        bm.current_price,
        "coupon":               bm.coupon,
        "maturity_years":       bm.maturity_years,
        "ytm":                  bm.ytm,
        "ytc":                  bm.ytc,
        "current_yield":        bm.current_yield,
        "real_yield":           bm.real_yield,
        "country":              bm.country,
        "breakeven_inflation":  bm.breakeven_inflation,
        "issuer":               bm.issuer,
        "sector":               bm.sector,
        "signal":               _sv(bm.signal),
    }


def _bond_duration_out(bd) -> Optional[dict]:
    if bd is None:
        return None
    return {
        "macaulay_duration":  bd.macaulay_duration,
        "modified_duration":  bd.modified_duration,
        "convexity":          bd.convexity,
        "dv01":               bd.dv01,
        "signal":             _sv(bd.signal),
    }


def _bond_credit_out(bc) -> Optional[dict]:
    if bc is None:
        return None
    return {
        "moodys":               bc.moodys,
        "sp":                   bc.sp,
        "fitch":                bc.fitch,
        "category":             bc.category,
        "trend":                bc.trend,
        "default_probability":  bc.default_probability,
        "signal":               _sv(bc.signal),
    }


def _bond_spread_out(bs) -> Optional[dict]:
    if bs is None:
        return None
    return {
        "spread_bps":    bs.spread_bps,
        "oas":           bs.oas,
        "z_spread":      bs.z_spread,
        "spread_trend":  bs.spread_trend,
        "signal":        _sv(bs.signal),
    }


def _bond_result_out(br) -> Optional[dict]:
    if br is None:
        return None
    return {
        "ticker":    br.ticker,
        "bond_type": br.bond_type,
        "metrics":   _bond_metrics_out(br.metrics),
        "duration":  _bond_duration_out(br.duration),
        "credit":    _bond_credit_out(br.credit),
        "spread":    _bond_spread_out(br.spread),
        # Risikoaffinitäts-Aggregation (PR #19): das Gesamtsignal + die Affinität dürfen
        # den Cache-Round-Trip überleben, sonst fielen sie auf NEUTRAL/None zurück.
        "overall_signal": _sv(br.overall_signal),
        "confidence":     br.confidence,
        "risk_affinity":  _sv(br.risk_affinity),
        "credit_band":    _sv(br.credit_band),
    }


def _index_price_out(ip) -> Optional[dict]:
    if ip is None:
        return None
    return {
        "current_price": ip.current_price,
        "perf_1w":       ip.perf_1w,
        "perf_1m":       ip.perf_1m,
        "perf_3m":       ip.perf_3m,
        "perf_ytd":      ip.perf_ytd,
        "perf_1y":       ip.perf_1y,
        "perf_3y":       ip.perf_3y,
        "perf_5y":       ip.perf_5y,
        "high_52w":      ip.high_52w,
        "low_52w":       ip.low_52w,
        "signal":        _sv(ip.signal),
    }


def _index_valuation_out(iv) -> Optional[dict]:
    if iv is None:
        return None
    return {
        "pe_trailing":    iv.pe_trailing,
        "pe_forward":     iv.pe_forward,
        "shiller_cape":   iv.shiller_cape,
        "dividend_yield": iv.dividend_yield,
        "ev_ebitda":      iv.ev_ebitda,
        "signal":         _sv(iv.signal),
    }


def _index_earnings_out(ie) -> Optional[dict]:
    if ie is None:
        return None
    return {
        "eps_growth_1y":      ie.eps_growth_1y,
        "revenue_growth_1y":  ie.revenue_growth_1y,
        "operating_margin":   ie.operating_margin,
        "estimate_revision":  ie.estimate_revision,
        "signal":             _sv(ie.signal),
    }


def _index_breadth_out(ib) -> Optional[dict]:
    if ib is None:
        return None
    return {
        "pct_above_ma50":       ib.pct_above_ma50,
        "pct_above_ma200":      ib.pct_above_ma200,
        "advance_decline_ratio": ib.advance_decline_ratio,
        "new_highs":            ib.new_highs,
        "new_lows":             ib.new_lows,
        "signal":               _sv(ib.signal),
    }


def _index_momentum_out(im) -> Optional[dict]:
    if im is None:
        return None
    return {
        "rsi_14":           im.rsi_14,
        "ma50":             im.ma50,
        "ma200":            im.ma200,
        "golden_cross":     im.golden_cross,
        "relative_strength": im.relative_strength,
        "signal":           _sv(im.signal),
    }


def _sector_composition_out(sc) -> Optional[dict]:
    if sc is None:
        return None
    return {
        "top_sector":          sc.top_sector,
        "top_sector_weight":   sc.top_sector_weight,
        "top_holding":         sc.top_holding,
        "top_holding_weight":  sc.top_holding_weight,
        "top_10_concentration": sc.top_10_concentration,
        "signal":              _sv(sc.signal),
    }


def _index_valuation_range_out(ivr) -> Optional[dict]:
    if ivr is None:
        return None
    return {
        "eps_estimate":      ivr.eps_estimate,
        "pe_historical_low": ivr.pe_historical_low,
        "pe_historical_high": ivr.pe_historical_high,
        "price_low":         ivr.price_low,
        "price_mid":         ivr.price_mid,
        "price_high":        ivr.price_high,
        "current_price":     ivr.current_price,
        "position":          ivr.position,
        "signal":            _sv(ivr.signal),
    }


def _index_result_out(ir) -> Optional[dict]:
    if ir is None:
        return None
    return {
        "ticker":          ir.ticker,
        "price":           _index_price_out(ir.price),
        "valuation":       _index_valuation_out(ir.valuation),
        "earnings":        _index_earnings_out(ir.earnings),
        "breadth":         _index_breadth_out(ir.breadth),
        "momentum":        _index_momentum_out(ir.momentum),
        "composition":     _sector_composition_out(ir.composition),
        "valuation_range": _index_valuation_range_out(ir.valuation_range),
    }


def _supply_demand_out(sd) -> Optional[dict]:
    if sd is None:
        return None
    return {
        "inventory_current":      sd.inventory_current,
        "inventory_avg_5y":       sd.inventory_avg_5y,
        "inventory_pct_vs_avg":   sd.inventory_pct_vs_avg,
        "production_change_yoy":  sd.production_change_yoy,
        "stock_to_flow":          sd.stock_to_flow,
        "stock_to_flow_signal":   sd.stock_to_flow_signal,
        "signal":                 _sv(sd.signal),
    }


def _seasonality_out(s) -> Optional[dict]:
    if s is None:
        return None
    return {
        "current_month_bias":    s.current_month_bias,
        "avg_return_this_month": s.avg_return_this_month,
        "positive_years_pct":    s.positive_years_pct,
        "signal":                _sv(s.signal),
    }


def _cot_out(c) -> Optional[dict]:
    if c is None:
        return None
    return {
        "net_speculative_long":   c.net_speculative_long,
        "net_speculative_pct_oi": c.net_speculative_pct_oi,
        "signal":                 _sv(c.signal),
    }


def _commodity_valuation_range_out(cvr) -> Optional[dict]:
    if cvr is None:
        return None
    return {
        "current_price":        cvr.current_price,
        "price_low_5y":         cvr.price_low_5y,
        "price_high_5y":        cvr.price_high_5y,
        "percentile_5y":        cvr.percentile_5y,
        "percentile_10y":       cvr.percentile_10y,
        "production_cost_low":  cvr.production_cost_low,
        "production_cost_high": cvr.production_cost_high,
        "position":             cvr.position,
        "signal":               _sv(cvr.signal),
    }


def _commodity_deep_out(cd) -> Optional[dict]:
    if cd is None:
        return None
    return {
        "commodity":       cd.commodity,
        "supply_demand":   _supply_demand_out(cd.supply_demand),
        "seasonality":     _seasonality_out(cd.seasonality),
        "cot":             _cot_out(cd.cot),
        "valuation_range": _commodity_valuation_range_out(cd.valuation_range),
        # Aggregiertes Gesamturteil (Bug #47): muss den Round-Trip überleben,
        # sonst fällt es beim Laden still auf NEUTRAL/0.0 zurück (analog Bond, PR #19).
        "overall_signal":  _sv(cd.overall_signal),
        "confidence":      cd.confidence,
    }


# ─── Deserialize helpers ──────────────────────────────────────────────────────

def _sig(v) -> "Signal":
    from core.domain.models import Signal
    return Signal(v) if v else Signal.NEUTRAL


def _load_valuation_range(d):
    if d is None:
        return None
    from core.domain.models import ValuationRangeSnapshot, ValuationMethod, Signal
    methods = [
        ValuationMethod(name=m["name"], low=m["low"], high=m["high"], currency=m.get("currency", "USD"))
        for m in (d.get("methods") or [])
    ]
    return ValuationRangeSnapshot(
        methods=methods,
        combined_low=d["combined_low"],
        combined_high=d["combined_high"],
        current_price=d.get("current_price"),
        position=d.get("position", "unknown"),
        signal=_sig(d.get("signal")),
    )


def _load_precious_metals_result(d):
    if d is None:
        return None
    from core.domain.models import (
        PreciousMetalsResult, PreciousMetalSnapshot, CrossMetalSnapshot, Signal
    )
    pa = d.get("price_analysis")
    cm = d.get("cross_metal")
    price_analysis = PreciousMetalSnapshot(
        metal=pa["metal"],
        price_usd=pa.get("price_usd"),
        performance=pa.get("performance", {}),
        rsi=pa.get("rsi"),
        ma50=pa.get("ma50"),
        ma200=pa.get("ma200"),
        stock_to_flow=pa.get("stock_to_flow"),
        real_yield_correlation=pa.get("real_yield_correlation"),
        signal=_sig(pa.get("signal")),
    ) if pa else None
    cross_metal = CrossMetalSnapshot(
        gold_silver_ratio=cm.get("gold_silver_ratio"),
        gold_platinum_ratio=cm.get("gold_platinum_ratio"),
        signal=_sig(cm.get("signal")),
    ) if cm else None
    return PreciousMetalsResult(
        metal=d["metal"],
        price_analysis=price_analysis,
        cross_metal=cross_metal,
        valuation_range=_load_valuation_range(d.get("valuation_range")),
        cot_signal=_sig(d.get("cot_signal")),
        currency_impact=d.get("currency_impact", {}),
    )


def _load_bond_result(d):
    if d is None:
        return None
    from core.domain.models import (
        BondResult, BondMetricsSnapshot, BondDurationSnapshot,
        BondCreditSnapshot, BondSpreadSnapshot, RiskAffinity, CreditBand,
    )
    m = d.get("metrics") or {}
    dur = d.get("duration") or {}
    cr = d.get("credit") or {}
    sp = d.get("spread") or {}
    ra = d.get("risk_affinity")
    cb = d.get("credit_band")
    return BondResult(
        ticker=d["ticker"],
        bond_type=d["bond_type"],
        metrics=BondMetricsSnapshot(
            bond_type=m.get("bond_type", ""),
            current_price=m.get("current_price"),
            coupon=m.get("coupon"),
            maturity_years=m.get("maturity_years"),
            ytm=m.get("ytm"),
            ytc=m.get("ytc"),
            current_yield=m.get("current_yield"),
            real_yield=m.get("real_yield"),
            country=m.get("country"),
            breakeven_inflation=m.get("breakeven_inflation"),
            issuer=m.get("issuer"),
            sector=m.get("sector"),
            signal=_sig(m.get("signal")),
        ),
        duration=BondDurationSnapshot(
            macaulay_duration=dur.get("macaulay_duration"),
            modified_duration=dur.get("modified_duration"),
            convexity=dur.get("convexity"),
            dv01=dur.get("dv01"),
            signal=_sig(dur.get("signal")),
        ),
        credit=BondCreditSnapshot(
            moodys=cr.get("moodys"),
            sp=cr.get("sp"),
            fitch=cr.get("fitch"),
            category=cr.get("category", "investment_grade"),
            trend=cr.get("trend", "stable"),
            default_probability=cr.get("default_probability"),
            signal=_sig(cr.get("signal")),
        ),
        spread=BondSpreadSnapshot(
            spread_bps=sp.get("spread_bps"),
            oas=sp.get("oas"),
            z_spread=sp.get("z_spread"),
            spread_trend=sp.get("spread_trend", "stable"),
            signal=_sig(sp.get("signal")),
        ),
        # PR #19: Gesamtsignal + Affinität wiederherstellen (None bleibt None).
        overall_signal=_sig(d.get("overall_signal")),
        confidence=d.get("confidence", 0.0),
        risk_affinity=RiskAffinity(ra) if ra else None,
        credit_band=CreditBand(cb) if cb else None,
    )


def _load_index_result(d):
    if d is None:
        return None
    from core.domain.models import (
        IndexResult, IndexPriceSnapshot, IndexValuationSnapshot,
        IndexEarningsSnapshot, IndexBreadthSnapshot, IndexMomentumSnapshot,
        SectorCompositionSnapshot, IndexValuationRangeSnapshot,
    )
    p  = d.get("price") or {}
    v  = d.get("valuation") or {}
    e  = d.get("earnings") or {}
    b  = d.get("breadth") or {}
    mo = d.get("momentum") or {}
    co = d.get("composition") or {}
    vr = d.get("valuation_range") or {}
    return IndexResult(
        ticker=d["ticker"],
        price=IndexPriceSnapshot(
            current_price=p.get("current_price"),
            perf_1w=p.get("perf_1w"),
            perf_1m=p.get("perf_1m"),
            perf_3m=p.get("perf_3m"),
            perf_ytd=p.get("perf_ytd"),
            perf_1y=p.get("perf_1y"),
            perf_3y=p.get("perf_3y"),
            perf_5y=p.get("perf_5y"),
            high_52w=p.get("high_52w"),
            low_52w=p.get("low_52w"),
            signal=_sig(p.get("signal")),
        ),
        valuation=IndexValuationSnapshot(
            pe_trailing=v.get("pe_trailing"),
            pe_forward=v.get("pe_forward"),
            shiller_cape=v.get("shiller_cape"),
            dividend_yield=v.get("dividend_yield"),
            ev_ebitda=v.get("ev_ebitda"),
            signal=_sig(v.get("signal")),
        ),
        earnings=IndexEarningsSnapshot(
            eps_growth_1y=e.get("eps_growth_1y"),
            revenue_growth_1y=e.get("revenue_growth_1y"),
            operating_margin=e.get("operating_margin"),
            estimate_revision=e.get("estimate_revision", "stable"),
            signal=_sig(e.get("signal")),
        ),
        breadth=IndexBreadthSnapshot(
            pct_above_ma50=b.get("pct_above_ma50"),
            pct_above_ma200=b.get("pct_above_ma200"),
            advance_decline_ratio=b.get("advance_decline_ratio"),
            new_highs=b.get("new_highs"),
            new_lows=b.get("new_lows"),
            signal=_sig(b.get("signal")),
        ),
        momentum=IndexMomentumSnapshot(
            rsi_14=mo.get("rsi_14"),
            ma50=mo.get("ma50"),
            ma200=mo.get("ma200"),
            golden_cross=mo.get("golden_cross"),
            relative_strength=mo.get("relative_strength"),
            signal=_sig(mo.get("signal")),
        ),
        composition=SectorCompositionSnapshot(
            top_sector=co.get("top_sector"),
            top_sector_weight=co.get("top_sector_weight"),
            top_holding=co.get("top_holding"),
            top_holding_weight=co.get("top_holding_weight"),
            top_10_concentration=co.get("top_10_concentration"),
            signal=_sig(co.get("signal")),
        ),
        valuation_range=IndexValuationRangeSnapshot(
            eps_estimate=vr.get("eps_estimate"),
            pe_historical_low=vr.get("pe_historical_low"),
            pe_historical_high=vr.get("pe_historical_high"),
            price_low=vr.get("price_low"),
            price_mid=vr.get("price_mid"),
            price_high=vr.get("price_high"),
            current_price=vr.get("current_price"),
            position=vr.get("position", "unknown"),
            signal=_sig(vr.get("signal")),
        ),
    )


def _load_commodity_deep(d):
    if d is None:
        return None
    from core.domain.models import (
        CommodityBottomUpResult, SupplyDemandSnapshot,
        SeasonalitySnapshot, COTSnapshot, CommodityValuationRangeSnapshot,
    )
    sd  = d.get("supply_demand") or {}
    sea = d.get("seasonality") or {}
    cot = d.get("cot") or {}
    vr  = d.get("valuation_range") or {}
    return CommodityBottomUpResult(
        commodity=d["commodity"],
        supply_demand=SupplyDemandSnapshot(
            inventory_current=sd.get("inventory_current"),
            inventory_avg_5y=sd.get("inventory_avg_5y"),
            inventory_pct_vs_avg=sd.get("inventory_pct_vs_avg"),
            production_change_yoy=sd.get("production_change_yoy"),
            stock_to_flow=sd.get("stock_to_flow"),
            stock_to_flow_signal=sd.get("stock_to_flow_signal"),
            signal=_sig(sd.get("signal")),
        ),
        seasonality=SeasonalitySnapshot(
            current_month_bias=sea.get("current_month_bias", "neutral"),
            avg_return_this_month=sea.get("avg_return_this_month"),
            positive_years_pct=sea.get("positive_years_pct"),
            signal=_sig(sea.get("signal")),
        ),
        cot=COTSnapshot(
            net_speculative_long=cot.get("net_speculative_long"),
            net_speculative_pct_oi=cot.get("net_speculative_pct_oi"),
            signal=_sig(cot.get("signal")),
        ),
        valuation_range=CommodityValuationRangeSnapshot(
            current_price=vr.get("current_price"),
            price_low_5y=vr.get("price_low_5y"),
            price_high_5y=vr.get("price_high_5y"),
            percentile_5y=vr.get("percentile_5y"),
            percentile_10y=vr.get("percentile_10y"),
            production_cost_low=vr.get("production_cost_low"),
            production_cost_high=vr.get("production_cost_high"),
            position=vr.get("position", "fair"),
            signal=_sig(vr.get("signal")),
        ),
        # Bug #47: aggregiertes Gesamturteil aus dem Cache wiederherstellen.
        # Ältere Dateien ohne diese Felder fallen defensiv auf NEUTRAL/0.0 zurück.
        overall_signal=_sig(d.get("overall_signal")),
        confidence=d.get("confidence", 0.0),
    )


# ─── ResultCache ──────────────────────────────────────────────────────────────

class ResultCache:
    # --- Modus 1 ---

    def save_cockpit(self, result) -> None:
        ys_usa = result.yield_curve.yield_spreads.usa
        data = {
            "_saved_at":         datetime.now(timezone.utc).isoformat(),
            "regime":            result.macro.regime.value,
            "regime_confidence": result.macro.regime_confidence,
            "yield_usa_10y2y":   ys_usa.spread_10y2y,
            "yield_usa_10y3m":   ys_usa.spread_10y3m,
            "yield_usa_inverted": ys_usa.inverted,
            "vix":               result.sentiment.vix.vix,
            "vstoxx":            result.sentiment.vix.vstoxx,
            "fear_greed":        result.sentiment.fear_greed.value,
            "fear_greed_label":  result.sentiment.fear_greed.label,
            "put_call_ratio":    result.sentiment.put_call.ratio,
            "leading_usa":       result.sectors.performance.leading_usa,
            "lagging_usa":       result.sectors.performance.lagging_usa,
            "leading_eu":        result.sectors.performance.leading_eu,
            "lagging_eu":        result.sectors.performance.lagging_eu,
        }
        with open(COCKPIT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_cockpit(self) -> Optional[object]:
        if not _is_fresh(COCKPIT_FILE):
            return None
        from core.domain.models import (
            CockpitResult, MarketRegime, Signal,
            MacroChiefResult,
            InflationSnapshot, InflationDataPoint,
            MoneySupplySnapshot, MoneySupplyDataPoint,
            InterestRateSnapshot, InterestRateDataPoint,
            GDPSnapshot, GDPDataPoint,
            LaborIncomeSnapshot, LaborIncomeDataPoint,
            CreditSnapshot, CreditDataPoint,
            BuffettIndicatorSnapshot,
            CommodityChiefResult, EnergySnapshot, IndustrialMetalsSnapshot,
            PreciousMetalsMacroSnapshot, AgriculturalSnapshot,
            SentimentChiefResult, VIXSnapshot, FearGreedSnapshot, PutCallSnapshot,
            YieldCurveChiefResult, YieldSpreadDataPoint, YieldSpreadSnapshot,
            SovereignSpreadSnapshot,
            SectorChiefResult, SectorPerformanceSnapshot, SectorRotationSnapshot,
        )
        with open(COCKPIT_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)

        regime = MarketRegime(d["regime"])

        # ── Macro (minimal — only regime matters for judgment) ──────────────
        n_inf  = InflationDataPoint(None, None, None, None, None, Signal.NEUTRAL)
        n_ms   = MoneySupplyDataPoint(None, None, None, Signal.NEUTRAL)
        n_ir   = InterestRateDataPoint(None, "stable", None, None, Signal.NEUTRAL)
        n_gdp  = GDPDataPoint(None, None, None, None, None, Signal.NEUTRAL)
        n_lab  = LaborIncomeDataPoint(None, None, Signal.NEUTRAL)
        n_cred = CreditDataPoint(None, None, Signal.NEUTRAL)
        macro = MacroChiefResult(
            regime=regime,
            regime_confidence=d.get("regime_confidence", 0.0),
            inflation=InflationSnapshot(n_inf, n_inf, n_inf),
            money_supply=MoneySupplySnapshot(n_ms, n_ms, n_ms),
            interest_rate=InterestRateSnapshot(n_ir, n_ir, n_ir),
            gdp=GDPSnapshot(n_gdp, n_gdp, n_gdp),
            labor_income=LaborIncomeSnapshot(n_lab, n_lab, n_lab),
            credit=CreditSnapshot(n_cred, n_cred, n_cred),
            buffett_indicator=BuffettIndicatorSnapshot(countries={}, signal=Signal.NEUTRAL),
        )

        # ── Commodities (stub) ───────────────────────────────────────────────
        commodities = CommodityChiefResult(
            energy=EnergySnapshot(None, None, None, Signal.NEUTRAL),
            industrial_metals=IndustrialMetalsSnapshot(None, None, None, None, Signal.NEUTRAL),
            precious_metals=PreciousMetalsMacroSnapshot(None, None, None, None, None, None, Signal.NEUTRAL),
            agricultural=AgriculturalSnapshot(None, None, None, None, None, None, None, Signal.NEUTRAL),
        )

        # ── Sentiment ────────────────────────────────────────────────────────
        sentiment = SentimentChiefResult(
            vix=VIXSnapshot(vix=d.get("vix"), vstoxx=d.get("vstoxx"), signal=Signal.NEUTRAL),
            fear_greed=FearGreedSnapshot(
                value=d.get("fear_greed"),
                label=d.get("fear_greed_label", "Unknown"),
                signal=Signal.NEUTRAL,
            ),
            put_call=PutCallSnapshot(ratio=d.get("put_call_ratio"), signal=Signal.NEUTRAL),
        )

        # ── Yield Curve ──────────────────────────────────────────────────────
        inverted = d.get("yield_usa_inverted", False)
        usa_yield = YieldSpreadDataPoint(
            spread_10y2y=d.get("yield_usa_10y2y"),
            spread_10y3m=d.get("yield_usa_10y3m"),
            spread_30y10y=None,
            inverted=inverted,
            signal=Signal.BEARISH if inverted else Signal.NEUTRAL,
        )
        n_yield = YieldSpreadDataPoint(None, None, None, False, Signal.NEUTRAL)
        yield_curve = YieldCurveChiefResult(
            yield_spreads=YieldSpreadSnapshot(usa=usa_yield, eurozone=n_yield, switzerland=n_yield),
            sovereign_spreads=SovereignSpreadSnapshot(None, None, None, Signal.NEUTRAL),
        )

        # ── Sectors ──────────────────────────────────────────────────────────
        sectors = SectorChiefResult(
            performance=SectorPerformanceSnapshot(
                usa={}, eurozone={},
                leading_usa=d.get("leading_usa", ""),
                lagging_usa=d.get("lagging_usa", ""),
                leading_eu=d.get("leading_eu", ""),
                lagging_eu=d.get("lagging_eu", ""),
            ),
            rotation=SectorRotationSnapshot(
                recommended=[], avoid=[], alignment="mixed", signal=Signal.NEUTRAL,
            ),
        )

        return CockpitResult(
            macro=macro,
            commodities=commodities,
            sentiment=sentiment,
            yield_curve=yield_curve,
            sectors=sectors,
        )

    # --- Modus 2 ---

    def save_bottom_up(self, result) -> None:
        path = BOTTOMUP_FILE.format(ticker=result.ticker)
        fu  = result.fundamentals
        q   = result.quality
        si  = result.short_interest
        ins = result.insider
        et  = result.earnings_trend
        mo  = result.moat

        data = {
            "_saved_at":  datetime.now(timezone.utc).isoformat(),
            "ticker":     result.ticker,
            # Task 2: underlying/wrapper statt asset_class persistieren (Round-Trip-Bug #1).
            "underlying": result.underlying.value,
            "wrapper":    result.wrapper.value,

            # ── Equity fields ─────────────────────────────────────────────
            "fundamentals": {
                "pe_ratio":         fu.pe_ratio,
                "forward_pe":       fu.forward_pe,
                "shiller_cape":     fu.shiller_cape,
                "peg_ratio":        fu.peg_ratio,
                "ev_ebitda":        fu.ev_ebitda,
                "ev_revenue":       fu.ev_revenue,
                "price_book":       fu.price_book,
                "price_sales":      fu.price_sales,
                "price_fcf":        fu.price_fcf,
                "dividend_yield":   fu.dividend_yield,
                "wacc":             fu.wacc,
                "revenue_cagr_3y":  fu.revenue_cagr_3y,
                "operating_margin": fu.operating_margin,
                "gross_margin":     fu.gross_margin,
                "debt_to_equity":   fu.debt_to_equity,
                "signal":           _sv(fu.signal),
            } if fu else None,

            "quality": {
                "gross_margin":      q.gross_margin,
                "operating_margin":  q.operating_margin,
                "net_margin":        q.net_margin,
                "fcf_margin":        q.fcf_margin,
                "roe":               q.roe,
                "roa":               q.roa,
                "roic":              q.roic,
                "debt_to_equity":    q.debt_to_equity,
                "net_debt_ebitda":   q.net_debt_ebitda,
                "interest_coverage": q.interest_coverage,
                "current_ratio":     q.current_ratio,
                "altman_z":          q.altman_z,
                "signal":            _sv(q.signal),
            } if q else None,

            "short_interest": {
                "short_float_pct": si.short_float_pct,
                "days_to_cover":   si.days_to_cover,
                "signal":          _sv(si.signal),
            } if si else None,

            "insider": {
                "net_direction":       ins.net_direction,
                "recent_transactions": ins.recent_transactions,
                "signal":              _sv(ins.signal),
            } if ins else None,

            "earnings_trend": {
                "beat_rate":         et.beat_rate,
                "estimate_revision": et.estimate_revision,
                "signal":            _sv(et.signal),
            } if et else None,

            "moat": {
                "intangible_assets": _moat_score_out(mo.intangible_assets),
                "switching_costs":   _moat_score_out(mo.switching_costs),
                "network_effects":   _moat_score_out(mo.network_effects),
                "cost_advantages":   _moat_score_out(mo.cost_advantages),
                "efficient_scale":   _moat_score_out(mo.efficient_scale),
                "total_score":       mo.total_score,
                "overall":           mo.overall,
                "llm_reasoning":     mo.llm_reasoning,
                "signal":            _sv(mo.signal),
            } if mo else None,

            "valuation_range": _valuation_range_out(result.valuation_range),

            # ── Asset-class-specific fields ───────────────────────────────
            "precious_metals": _precious_metals_result_out(result.precious_metals),
            "bond":            _bond_result_out(result.bond),
            "index":           _index_result_out(result.index),
            "commodity_deep":  _commodity_deep_out(result.commodity_deep),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_bottom_up(self, ticker: str) -> Optional[object]:
        path = BOTTOMUP_FILE.format(ticker=ticker.upper())
        if not _is_fresh(path):
            return None
        from core.domain.models import (
            BottomUpResult, FundamentalsSnapshot, QualitySnapshot,
            ShortInterestSnapshot, InsiderSnapshot, EarningsTrendSnapshot,
            MoatSnapshot, MoatScore, Signal,
        )
        from core.domain.taxonomy import Underlying, Wrapper, legacy_to_taxonomy
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)

        fu_d  = d.get("fundamentals")
        q_d   = d.get("quality")
        si_d  = d.get("short_interest")
        ins_d = d.get("insider")
        et_d  = d.get("earnings_trend")
        mo_d  = d.get("moat")

        fundamentals = FundamentalsSnapshot(
            pe_ratio=fu_d.get("pe_ratio"),
            forward_pe=fu_d.get("forward_pe"),
            shiller_cape=fu_d.get("shiller_cape"),
            peg_ratio=fu_d.get("peg_ratio"),
            ev_ebitda=fu_d.get("ev_ebitda"),
            ev_revenue=fu_d.get("ev_revenue"),
            price_book=fu_d.get("price_book"),
            price_sales=fu_d.get("price_sales"),
            price_fcf=fu_d.get("price_fcf"),
            dividend_yield=fu_d.get("dividend_yield"),
            wacc=fu_d.get("wacc"),
            revenue_cagr_3y=fu_d.get("revenue_cagr_3y"),
            operating_margin=fu_d.get("operating_margin"),
            gross_margin=fu_d.get("gross_margin"),
            debt_to_equity=fu_d.get("debt_to_equity"),
            signal=_sig(fu_d.get("signal")),
        ) if fu_d else None

        quality = QualitySnapshot(
            gross_margin=q_d.get("gross_margin"),
            operating_margin=q_d.get("operating_margin"),
            net_margin=q_d.get("net_margin"),
            fcf_margin=q_d.get("fcf_margin"),
            roe=q_d.get("roe"),
            roa=q_d.get("roa"),
            roic=q_d.get("roic"),
            debt_to_equity=q_d.get("debt_to_equity"),
            net_debt_ebitda=q_d.get("net_debt_ebitda"),
            interest_coverage=q_d.get("interest_coverage"),
            current_ratio=q_d.get("current_ratio"),
            altman_z=q_d.get("altman_z"),
            signal=_sig(q_d.get("signal")),
        ) if q_d else None

        short_interest = ShortInterestSnapshot(
            short_float_pct=si_d.get("short_float_pct"),
            days_to_cover=si_d.get("days_to_cover"),
            signal=_sig(si_d.get("signal")),
        ) if si_d else None

        insider = InsiderSnapshot(
            net_direction=ins_d.get("net_direction", ""),
            recent_transactions=ins_d.get("recent_transactions", 0),
            signal=_sig(ins_d.get("signal")),
        ) if ins_d else None

        earnings_trend = EarningsTrendSnapshot(
            beat_rate=et_d.get("beat_rate"),
            estimate_revision=et_d.get("estimate_revision", "stable"),
            signal=_sig(et_d.get("signal")),
        ) if et_d else None

        def _ms(x):
            return MoatScore(score=x["score"], evidence=x["evidence"]) if x else MoatScore(0, "")

        moat = MoatSnapshot(
            intangible_assets=_ms(mo_d.get("intangible_assets")),
            switching_costs=_ms(mo_d.get("switching_costs")),
            network_effects=_ms(mo_d.get("network_effects")),
            cost_advantages=_ms(mo_d.get("cost_advantages")),
            efficient_scale=_ms(mo_d.get("efficient_scale")),
            total_score=mo_d.get("total_score", 0),
            overall=mo_d.get("overall", "none"),
            llm_reasoning=mo_d.get("llm_reasoning", ""),
            signal=_sig(mo_d.get("signal")),
        ) if mo_d else None

        # Task 2: underlying/wrapper aus dem Cache laden; ältere Dateien ohne diese Felder
        # werden defensiv via legacy_to_taxonomy auf den bekannten asset_class-String gemappt.
        if "underlying" in d and "wrapper" in d:
            underlying = Underlying(d["underlying"])
            wrapper    = Wrapper(d["wrapper"])
        else:
            underlying, wrapper = legacy_to_taxonomy(d.get("asset_class", "equity"))

        return BottomUpResult(
            ticker=d["ticker"],
            underlying=underlying,
            wrapper=wrapper,
            fundamentals=fundamentals,
            quality=quality,
            short_interest=short_interest,
            insider=insider,
            earnings_trend=earnings_trend,
            moat=moat,
            valuation_range=_load_valuation_range(d.get("valuation_range")),
            precious_metals=_load_precious_metals_result(d.get("precious_metals")),
            bond=_load_bond_result(d.get("bond")),
            index=_load_index_result(d.get("index")),
            commodity_deep=_load_commodity_deep(d.get("commodity_deep")),
        )
