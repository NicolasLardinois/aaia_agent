import json
import logging
import os
import time
import urllib.parse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

import psycopg2
import psycopg2.extras

from core.ports.memory_port import MemoryPort

_log = logging.getLogger(__name__)

# Sentinel: unterscheidet "Feldzugriff fehlgeschlagen" von "Wert ist None".
_MISSING = object()


def _safe_value(getter, *, what: str):
    """Liest einen (ggf. verschachtelten) Wert defensiv aus.

    Schlägt der Zugriff fehl — typischer Fall: ein umbenanntes/fehlendes
    CockpitResult-/BottomUpResult-Unterfeld — wird der Fehler GELOGGT statt
    still verschluckt und ``_MISSING`` zurückgegeben, sodass der Aufrufer nur
    diesen einen Wert überspringt (granular), nicht alle folgenden.
    (Verwandt mit dem geplanten zentralen ``_safe``-Helfer, siehe §7 im Logbuch.)
    """
    try:
        return getter()
    except AttributeError:
        _log.warning("Snapshot-Feld %r nicht lesbar (umbenanntes/fehlendes Feld?)", what, exc_info=True)
        return _MISSING


def _put(snap: dict, key: str, getter, *, allow_none: bool = False) -> None:
    """Setzt ``snap[key]`` defensiv. Bei Lesefehler: loggen + überspringen.
    Bei erfolgreich gelesenem ``None`` nur setzen, wenn ``allow_none`` gilt."""
    value = _safe_value(getter, what=key)
    if value is _MISSING:
        return
    if value is not None or allow_none:
        snap[key] = value


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
    # Jeder Indikator wird einzeln und defensiv gelesen: ein umbenanntes Feld
    # überspringt nur sich selbst (+ Log), statt den ganzen Snapshot zu leeren.
    _put(snap, "vix", lambda: cockpit.sentiment.vix.vix)
    _put(snap, "fear_greed", lambda: cockpit.sentiment.fear_greed.value)
    _put(snap, "regime_confidence", lambda: cockpit.macro.regime_confidence, allow_none=True)
    _put(snap, "yield_spread_10y2y", lambda: cockpit.yield_curve.yield_spreads.usa.spread_10y2y)
    _put(snap, "inflation_cpi_usa", lambda: cockpit.macro.inflation.usa.cpi)
    return snap


class SupabaseMemory(MemoryPort):

    def __init__(self):
        self._url = os.getenv("SUPABASE_DB_URL")
        if not self._url:
            raise RuntimeError("SUPABASE_DB_URL nicht gesetzt.")

    @contextmanager
    def _connect(self):
        r = urllib.parse.urlparse(self._url)
        params = dict(
            host=r.hostname,
            port=r.port or 5432,
            user=r.username,
            password=urllib.parse.unquote(r.password or ""),
            dbname=r.path.lstrip("/"),
            cursor_factory=psycopg2.extras.RealDictCursor,
            sslmode="require",
        )
        conn = None
        for attempt in range(3):
            try:
                conn = psycopg2.connect(**params)
                break
            except psycopg2.Error:
                if attempt == 2:
                    raise
                time.sleep(2)
        try:
            yield conn
        finally:
            if conn is not None:
                conn.close()

    # ── Analyse speichern ───────────────────────────────────────────────

    def save_analysis(self, result, cockpit=None, price: Optional[float] = None) -> None:
        resolved_price = price if price is not None else _extract_price(result)
        indicators = _build_indicators_snapshot(cockpit)

        bu = result.bottom_up
        if bu:
            _put(indicators, "pe_ratio",
                 lambda: bu.fundamentals.pe_ratio if bu.fundamentals else None)
            _put(indicators, "short_float_pct",
                 lambda: bu.short_interest.short_float_pct if bu.short_interest else None)
            _put(indicators, "insider_transactions",
                 lambda: bu.insider.recent_transactions if bu.insider else None)

        # Bond-Recompute-Bausteine: defensiv einsammeln (ein fehlendes Feld überspringt nur sich selbst).
        bond = getattr(bu, "bond", None) if bu else None
        risk_affinity_val = None
        if bond is not None:
            ra = getattr(bond, "risk_affinity", None)
            risk_affinity_val = ra.value if ra is not None else None
            cb = getattr(bond, "credit_band", None)
            if cb is not None:
                indicators["bond_credit_band"] = cb.value
            for feld, attr in (("bond_metrics_signal", "metrics"),
                               ("bond_duration_signal", "duration"),
                               ("bond_spread_signal", "spread")):
                _put(indicators, feld, lambda a=attr: getattr(bond, a).signal.value)

        if getattr(result, "conflict_resolution", None):
            indicators["conflict_verdict"] = result.conflict_resolution.verdict
            indicators["conflict_reasoning"] = result.conflict_resolution.reasoning

        regime = None
        regime_conf = None
        if cockpit:
            # Granular: bricht z. B. `regime`, wird `regime_confidence` trotzdem gelesen.
            regime_val = _safe_value(lambda: cockpit.macro.regime.value, what="regime")
            if regime_val is not _MISSING:
                regime = regime_val
            conf_val = _safe_value(lambda: cockpit.macro.regime_confidence, what="regime_confidence")
            if conf_val is not _MISSING:
                regime_conf = conf_val

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analysis_memory (
                        ticker, asset_class, market, regime, regime_confidence,
                        top_down_context, alignment, dominant_signal, recommendation,
                        short_action,
                        confidence, xai_explanation, price_at_analysis,
                        top_down_anomaly_severity, bottom_up_anomaly_severity,
                        indicators_snapshot,
                        risk_affinity
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
                        # Short-Aktion separat persistieren: die Long-Linse deferiert bei
                        # Short-Positionen auf NONE, daher steckt der echte COVER/HOLD/SHORT
                        # nur in short_action — nötig für die Short-Alignment-Warnung im Monitor.
                        result.short_action.value,
                        result.confidence,
                        result.xai_explanation,
                        resolved_price,
                        result.top_down_anomaly.severity if result.top_down_anomaly else "none",
                        result.bottom_up_anomaly.severity if result.bottom_up_anomaly else "none",
                        json.dumps(indicators),
                        # Bond-Risikoaffinität separat persistieren: ermöglicht direktes Filtern/Sortieren
                        # nach Risikoaffinität im Monitor ohne JSON-Parsing des indicators_snapshot.
                        risk_affinity_val,
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

    # Risiko-Kennzahlen ohne eigene Spalte werden gebündelt als JSON in `metrics` persistiert
    # (eine jsonb-Spalte, zukunftssicher: neue Kennzahlen brauchen keine weitere Migration).
    _SNAPSHOT_METRIC_KEYS = (
        "long_value", "short_value", "net_exposure", "gross_exposure",
        "concentration_hhi", "portfolio_volatility", "portfolio_max_drawdown",
        "net_beta", "net_beta_pct",
    )

    def save_portfolio_snapshot(self, snapshot: dict) -> None:
        metrics = {k: snapshot.get(k) for k in self._SNAPSHOT_METRIC_KEYS}
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolio_snapshots (
                        total_positions, total_value_usd,
                        cluster_risks, alerts, overall_health, metrics
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        snapshot.get("total_positions", 0),
                        snapshot.get("total_value_usd"),
                        json.dumps(snapshot.get("cluster_risks", [])),
                        json.dumps(snapshot.get("alerts", [])),
                        snapshot.get("overall_health", "green"),
                        json.dumps(metrics),
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
                if not row:
                    return None
                snap = dict(row)
                # metrics-Container wieder ins Top-Level entpacken → Snapshot-Form wie gespeichert
                # (jsonb kommt je nach Treiber als dict oder str zurück — beides behandeln).
                metrics = snap.pop("metrics", None)
                if metrics:
                    if isinstance(metrics, str):
                        metrics = json.loads(metrics)
                    snap.update(metrics)
                return snap
