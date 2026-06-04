import json
import os
from datetime import datetime, timedelta
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
    return datetime.utcnow() - saved_at < MAX_AGE


class ResultCache:
    # --- Modus 1 ---

    def save_cockpit(self, result) -> None:
        ys_usa = result.yield_curve.yield_spreads.usa
        data = {
            "_saved_at":         datetime.utcnow().isoformat(),
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
            MacroChiefResult, MarketRegime,
            InflationSnapshot, InflationDataPoint,
            MoneySupplySnapshot, MoneySupplyDataPoint,
            InterestRateSnapshot, InterestRateDataPoint,
            GDPSnapshot, GDPDataPoint,
            ShillerCAPESnapshot, ShillerCAPEDataPoint,
            LaborIncomeSnapshot, LaborIncomeDataPoint,
            CreditSnapshot, CreditDataPoint,
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
        n_cape = ShillerCAPEDataPoint(None, 17.0, None, Signal.NEUTRAL)
        n_lab  = LaborIncomeDataPoint(None, None, Signal.NEUTRAL)
        n_cred = CreditDataPoint(None, None, Signal.NEUTRAL)
        macro = MacroChiefResult(
            regime=regime,
            regime_confidence=d.get("regime_confidence", 0.0),
            inflation=InflationSnapshot(n_inf, n_inf, n_inf),
            money_supply=MoneySupplySnapshot(n_ms, n_ms, n_ms),
            interest_rate=InterestRateSnapshot(n_ir, n_ir, n_ir),
            gdp=GDPSnapshot(n_gdp, n_gdp, n_gdp),
            shiller_cape=ShillerCAPESnapshot(n_cape, n_cape, n_cape),
            labor_income=LaborIncomeSnapshot(n_lab, n_lab, n_lab),
            credit=CreditSnapshot(n_cred, n_cred, n_cred),
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
        si  = result.short_interest
        ins = result.insider
        et  = result.earnings_trend
        data = {
            "_saved_at":   datetime.utcnow().isoformat(),
            "ticker":      result.ticker,
            "asset_class": result.asset_class,
            "fundamentals": {
                "pe_ratio":        fu.pe_ratio        if fu else None,
                "revenue_cagr_3y": fu.revenue_cagr_3y if fu else None,
                "operating_margin": fu.operating_margin if fu else None,
                "debt_to_equity":  fu.debt_to_equity  if fu else None,
                "signal":          fu.signal.value     if fu else "neutral",
            } if fu else None,
            "short_interest": {
                "short_float_pct": si.short_float_pct,
                "days_to_cover":   si.days_to_cover,
                "signal":          si.signal.value,
            } if si else None,
            "insider": {
                "net_direction":       ins.net_direction,
                "recent_transactions": ins.recent_transactions,
                "signal":              ins.signal.value,
            } if ins else None,
            "earnings_trend": {
                "beat_rate":         et.beat_rate,
                "estimate_revision": et.estimate_revision,
                "signal":            et.signal.value,
            } if et else None,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_bottom_up(self, ticker: str) -> Optional[object]:
        path = BOTTOMUP_FILE.format(ticker=ticker.upper())
        if not _is_fresh(path):
            return None
        from core.domain.models import (
            BottomUpResult, FundamentalsSnapshot, ShortInterestSnapshot,
            InsiderSnapshot, EarningsTrendSnapshot, Signal,
        )
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)

        fu_d  = d.get("fundamentals")
        si_d  = d.get("short_interest")
        ins_d = d.get("insider")
        et_d  = d.get("earnings_trend")

        fundamentals = FundamentalsSnapshot(
            pe_ratio=fu_d["pe_ratio"], forward_pe=None, shiller_cape=None,
            peg_ratio=None, ev_ebitda=None, ev_revenue=None,
            price_book=None, price_sales=None, price_fcf=None,
            dividend_yield=None, wacc=None,
            revenue_cagr_3y=fu_d["revenue_cagr_3y"],
            operating_margin=fu_d["operating_margin"],
            gross_margin=None,
            debt_to_equity=fu_d["debt_to_equity"],
            signal=Signal(fu_d["signal"]),
        ) if fu_d else None

        short_interest = ShortInterestSnapshot(
            short_float_pct=si_d["short_float_pct"],
            days_to_cover=si_d["days_to_cover"],
            signal=Signal(si_d["signal"]),
        ) if si_d else None

        insider = InsiderSnapshot(
            net_direction=ins_d["net_direction"],
            recent_transactions=ins_d["recent_transactions"],
            signal=Signal(ins_d["signal"]),
        ) if ins_d else None

        earnings_trend = EarningsTrendSnapshot(
            beat_rate=et_d["beat_rate"],
            estimate_revision=et_d["estimate_revision"],
            signal=Signal(et_d["signal"]),
        ) if et_d else None

        return BottomUpResult(
            ticker=d["ticker"],
            asset_class=d.get("asset_class", "equity"),
            fundamentals=fundamentals,
            quality=None,
            short_interest=short_interest,
            insider=insider,
            earnings_trend=earnings_trend,
            moat=None,
            valuation_range=None,
            precious_metals=None,
            bond=None,
        )
