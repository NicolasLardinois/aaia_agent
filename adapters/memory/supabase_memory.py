import json
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional

import psycopg2
import psycopg2.extras

from core.ports.memory_port import MemoryPort


def _extract_price(result) -> Optional[float]:
    bu = result.bottom_up
    if bu is None:
        return None
    if bu.valuation_range and bu.valuation_range.current_price is not None:
        return bu.valuation_range.current_price
    if bu.index and bu.index.price and bu.index.price.current_price is not None:
        return bu.index.price.current_price
    if bu.precious_metals and bu.precious_metals.price_analysis:
        return bu.precious_metals.price_analysis.price_usd
    if bu.commodity_deep and bu.commodity_deep.valuation_range:
        return bu.commodity_deep.valuation_range.current_price
    return None


def _build_indicators_snapshot(cockpit) -> dict:
    if cockpit is None:
        return {}
    snap: dict = {}
    try:
        if cockpit.sentiment.vix.vix is not None:
            snap["vix"] = cockpit.sentiment.vix.vix
        if cockpit.sentiment.fear_greed.value is not None:
            snap["fear_greed"] = cockpit.sentiment.fear_greed.value
        snap["regime_confidence"] = cockpit.macro.regime_confidence
        s = cockpit.yield_curve.yield_spreads.usa
        if s.spread_10y2y is not None:
            snap["yield_spread_10y2y"] = s.spread_10y2y
        if cockpit.macro.inflation.usa.cpi is not None:
            snap["inflation_cpi_usa"] = cockpit.macro.inflation.usa.cpi
    except AttributeError:
        pass
    return snap


class SupabaseMemory(MemoryPort):

    def __init__(self):
        self._url = os.getenv("SUPABASE_DB_URL")
        if not self._url:
            raise RuntimeError("SUPABASE_DB_URL nicht gesetzt.")

    def _connect(self):
        r = urllib.parse.urlparse(self._url)
        return psycopg2.connect(
            host=r.hostname,
            port=r.port or 5432,
            user=r.username,
            password=urllib.parse.unquote(r.password or ""),
            dbname=r.path.lstrip("/"),
            cursor_factory=psycopg2.extras.RealDictCursor,
            sslmode="require",
        )

    # ── Analyse speichern ───────────────────────────────────────────────

    def save_analysis(self, result, cockpit=None, price: Optional[float] = None) -> None:
        resolved_price = price if price is not None else _extract_price(result)
        indicators = _build_indicators_snapshot(cockpit)

        bu = result.bottom_up
        if bu:
            try:
                if bu.fundamentals and bu.fundamentals.pe_ratio is not None:
                    indicators["pe_ratio"] = bu.fundamentals.pe_ratio
                if bu.short_interest and bu.short_interest.short_float_pct is not None:
                    indicators["short_float_pct"] = bu.short_interest.short_float_pct
                if bu.insider and bu.insider.recent_transactions is not None:
                    indicators["insider_transactions"] = bu.insider.recent_transactions
            except AttributeError:
                pass

        regime = None
        regime_conf = None
        if cockpit:
            try:
                regime = cockpit.macro.regime.value
                regime_conf = cockpit.macro.regime_confidence
            except AttributeError:
                pass

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analysis_memory (
                        ticker, asset_class, market, regime, regime_confidence,
                        top_down_context, alignment, dominant_signal, recommendation,
                        confidence, xai_explanation, price_at_analysis,
                        top_down_anomaly_severity, bottom_up_anomaly_severity,
                        indicators_snapshot
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        result.ticker,
                        result.asset_class,
                        result.market,
                        regime,
                        regime_conf,
                        result.top_down_context,
                        result.alignment,
                        result.dominant_signal,
                        result.recommendation.action.value,
                        result.confidence,
                        result.xai_explanation,
                        resolved_price,
                        "none",
                        "none",
                        json.dumps(indicators),
                    ),
                )
            conn.commit()

    # ── History laden ───────────────────────────────────────────────────

    def load_history(self, ticker: str, days: int = 90) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM analysis_memory
                    WHERE ticker = %s AND timestamp >= %s
                    ORDER BY timestamp DESC
                    """,
                    (ticker, cutoff),
                )
                return [dict(row) for row in cur.fetchall()]

    def load_global_history(self, days: int = 90) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM analysis_memory
                    WHERE timestamp >= %s
                    ORDER BY timestamp DESC
                    """,
                    (cutoff,),
                )
                return [dict(row) for row in cur.fetchall()]

    # ── Backtester ──────────────────────────────────────────────────────

    def load_latest_backtester_report(self, backtester_type: str) -> dict:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM backtester_reports
                    WHERE backtester_type = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (backtester_type,),
                )
                row = cur.fetchone()
                return dict(row) if row else {}

    def save_backtester_report(self, report: dict) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backtester_reports (
                        backtester_type, ticker, original_recommendation,
                        price_at_recommendation, price_today, return_pct,
                        verdict, accuracy_30d, accuracy_60d, accuracy_90d, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        report.get("backtester_type"),
                        report.get("ticker"),
                        report.get("original_recommendation"),
                        report.get("price_at_recommendation"),
                        report.get("price_today"),
                        report.get("return_pct"),
                        report.get("verdict"),
                        report.get("accuracy_30d"),
                        report.get("accuracy_60d"),
                        report.get("accuracy_90d"),
                        report.get("notes"),
                    ),
                )
            conn.commit()

    # ── Portfolio ───────────────────────────────────────────────────────

    def save_portfolio_snapshot(self, snapshot: dict) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolio_snapshots (
                        total_positions, total_value_usd,
                        cluster_risks, alerts, overall_health
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        snapshot.get("total_positions", 0),
                        snapshot.get("total_value_usd"),
                        json.dumps(snapshot.get("cluster_risks", [])),
                        json.dumps(snapshot.get("alerts", [])),
                        snapshot.get("overall_health", "green"),
                    ),
                )
            conn.commit()

    def load_latest_portfolio_snapshot(self) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT 1"
                )
                row = cur.fetchone()
                return dict(row) if row else None
