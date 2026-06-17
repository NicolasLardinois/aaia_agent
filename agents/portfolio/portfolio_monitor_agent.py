import json
import os
from typing import Callable, Optional

import yfinance as yf

from core.ports.memory_port import MemoryPort
from core.utils.performance_metrics import max_drawdown

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "portfolio.json")

SECTOR_THRESHOLD      = 0.40
ASSET_CLASS_THRESHOLD = 0.60   # verschärft von 0.80
COUNTRY_THRESHOLD     = 0.70
LOSS_THRESHOLD        = 0.15
BASE_CURRENCY         = "USD"


def _fetch_current_price(ticker: str) -> Optional[float]:
    try:
        return float(yf.Ticker(ticker).fast_info["last_price"])
    except Exception:
        return None


def _default_fx_rate(from_ccy: str, to_ccy: str = BASE_CURRENCY) -> float:
    if from_ccy == to_ccy:
        return 1.0
    try:
        px = yf.Ticker(f"{from_ccy}{to_ccy}=X").fast_info["last_price"]
        return float(px) if px else 1.0
    except Exception:
        return 1.0


def _herfindahl(weights: list[float]) -> float:
    return round(sum(w * w for w in weights), 4) if weights else 0.0


def _check_cluster_risks(positions: list[dict]) -> list[dict]:
    if not positions:
        return []
    total_value = sum(p.get("_value_base", p["shares"] * p["current_price"]) for p in positions)
    if total_value == 0:
        return []
    risks = []
    thresholds = {
        "sector":      SECTOR_THRESHOLD,
        "asset_class": ASSET_CLASS_THRESHOLD,
        "country":     COUNTRY_THRESHOLD,
    }
    for dim, threshold in thresholds.items():
        buckets: dict[str, float] = {}
        for p in positions:
            val  = p.get("_value_base", p["shares"] * p["current_price"])
            name = p.get(dim, "Unbekannt")
            buckets[name] = buckets.get(name, 0.0) + val
        for name, val in buckets.items():
            pct = val / total_value
            if pct > threshold:
                risks.append({
                    "type":      dim,
                    "name":      name,
                    "pct":       round(pct, 3),
                    "threshold": threshold,
                    "message":   (
                        f"Klumpenrisiko {dim.replace('_', '-').title()}: "
                        f"{name} = {pct:.0%} (Grenze: {threshold:.0%})"
                    ),
                })
    return risks


class PortfolioMonitorAgent:

    def __init__(
        self,
        memory: MemoryPort,
        market_provider=None,
        fx_rate: Callable[[str, str], float] = _default_fx_rate,
        returns_provider: Optional[Callable[[str], list]] = None,
    ):
        self.memory = memory
        self.fx_rate = fx_rate
        self.returns_provider = returns_provider

    def _evaluate_positions(self, positions: list[dict]) -> dict:
        if not positions:
            return {
                "total_positions": 0,
                "total_value_usd": 0.0,
                "cluster_risks":   [],
                "alerts":          [],
                "overall_health":  "green",
                "concentration_hhi": 0.0,
                "portfolio_volatility": 0.0,
                "portfolio_max_drawdown": 0.0,
            }

        for p in positions:
            if "current_price" not in p:
                price = _fetch_current_price(p["ticker"])
                p["current_price"] = price if price else p["buy_price"]
            ccy = p.get("currency", BASE_CURRENCY)
            p["_fx"] = self.fx_rate(ccy, BASE_CURRENCY)
            p["_value_base"] = p["shares"] * p["current_price"] * p["_fx"]

        total_value   = sum(p["_value_base"] for p in positions)
        cluster_risks = _check_cluster_risks(positions)
        alerts: list[str] = [r["message"] for r in cluster_risks]

        for p in positions:
            if p["buy_price"] > 0:
                loss_pct = (p["current_price"] - p["buy_price"]) / p["buy_price"]
                if loss_pct < -LOSS_THRESHOLD:
                    alerts.append(
                        f"Offener Verlust {p['ticker']}: {loss_pct:.0%} "
                        f"(Kauf: {p['buy_price']:.2f}, Heute: {p['current_price']:.2f})"
                    )

        for p in positions:
            history = self.memory.load_history(p["ticker"], days=90)
            if history:
                last_rec = history[0].get("recommendation", "")
                if last_rec in ("SELL", "SHORT"):
                    alerts.append(
                        f"Alignment-Warnung {p['ticker']}: letzte Analyse = {last_rec}, "
                        f"Position aber noch gehalten."
                    )

        # Konzentration (HHI) über FX-konvertierte Gewichte
        weights = [p["_value_base"] / total_value for p in positions] if total_value > 0 else []
        hhi = _herfindahl(weights)

        # Portfolio-Vola/MaxDD aus gewichteten Positions-Returns (sofern Provider vorhanden)
        port_vol = 0.0
        port_mdd = 0.0
        if self.returns_provider and total_value > 0:
            series = []
            for p in positions:
                rets = self.returns_provider(p["ticker"]) or []
                if rets:
                    series.append((p["_value_base"] / total_value, rets))
            if series:
                n = min(len(r) for _, r in series)
                port_returns = [
                    sum(w * r[i] for w, r in series) for i in range(n)
                ]
                if len(port_returns) >= 2:
                    mean = sum(port_returns) / len(port_returns)
                    var = sum((x - mean) ** 2 for x in port_returns) / (len(port_returns) - 1)
                    port_vol = round(var ** 0.5, 4)
                port_mdd = round(max_drawdown(port_returns), 4)

        n_alerts = len(alerts)
        health   = "green" if n_alerts == 0 else ("yellow" if n_alerts <= 2 else "red")

        return {
            "total_positions": len(positions),
            "total_value_usd": round(total_value, 2),
            "cluster_risks":   cluster_risks,
            "alerts":          alerts,
            "overall_health":  health,
            "concentration_hhi": hhi,
            "portfolio_volatility": port_vol,
            "portfolio_max_drawdown": port_mdd,
        }

    async def run(self) -> None:
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print("[PortfolioMonitor] portfolio.json nicht gefunden — übersprungen.")
            return

        positions = data.get("positions", [])
        if not positions:
            print("[PortfolioMonitor] Keine Positionen erfasst — übersprungen.")
            return

        snapshot = self._evaluate_positions(positions)
        self.memory.save_portfolio_snapshot(snapshot)

        health = snapshot["overall_health"].upper()
        print(f"[PortfolioMonitor] Gesundheit: {health} | "
              f"{len(snapshot['alerts'])} Warnungen | "
              f"Wert: ${snapshot['total_value_usd']:,.0f}")
        for alert in snapshot["alerts"]:
            print(f"  ⚠ {alert}")
