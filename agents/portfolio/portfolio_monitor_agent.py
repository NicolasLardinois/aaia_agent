import os
from typing import Callable, Optional

import yfinance as yf

from core.domain.portfolio import Position, PortfolioError
from core.ports.memory_port import MemoryPort
from core.ports.portfolio_port import PortfolioPort
from core.utils.performance_metrics import max_drawdown

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


def _check_cluster_risks(positions: list[Position], values: list[float], gross: float) -> list[dict]:
    if gross == 0:
        return []
    risks = []
    thresholds = {"sector": SECTOR_THRESHOLD, "asset_class": ASSET_CLASS_THRESHOLD, "country": COUNTRY_THRESHOLD}
    for dim, threshold in thresholds.items():
        buckets: dict[str, float] = {}
        for p, val in zip(positions, values):
            signed = val if p.direction == "long" else -val
            name = getattr(p, dim, "Unbekannt")
            buckets[name] = buckets.get(name, 0.0) + signed
        for name, net in buckets.items():
            pct = abs(net) / gross
            if pct > threshold:
                risks.append({
                    "type":      dim,
                    "name":      name,
                    "pct":       round(pct, 3),
                    "threshold": threshold,
                    "message":   (
                        f"Klumpenrisiko {dim.replace('_', '-').title()}: "
                        f"{name} = {pct:.0%} netto (Grenze: {threshold:.0%})"
                    ),
                })
    return risks


class PortfolioMonitorAgent:

    def __init__(
        self,
        memory: MemoryPort,
        portfolio_port: PortfolioPort,
        market_provider=None,
        fx_rate: Callable[[str, str], float] = _default_fx_rate,
        returns_provider: Optional[Callable[[str], list]] = None,
    ):
        self.memory = memory
        self.portfolio_port = portfolio_port
        self.fx_rate = fx_rate
        self.returns_provider = returns_provider

    def _evaluate_positions(self, positions: list[Position]) -> dict:
        if not positions:
            return {
                "total_positions":         0,
                "total_value_usd":         0.0,
                "long_value":              0.0,
                "short_value":             0.0,
                "net_exposure":            0.0,
                "gross_exposure":          0.0,
                "cluster_risks":           [],
                "alerts":                  [],
                "overall_health":          "green",
                "concentration_hhi":       0.0,
                "portfolio_volatility":    0.0,
                "portfolio_max_drawdown":  0.0,
            }

        # Aktuellen Kurs ermitteln und Positionswert in Basiswährung berechnen
        values: list[float] = []
        cur_prices: list[float] = []
        for p in positions:
            cur = p.current_price if p.current_price is not None else (_fetch_current_price(p.ticker) or p.entry_price)
            cur_prices.append(cur)
            val = p.shares * cur * self.fx_rate(p.currency, BASE_CURRENCY)
            values.append(val)

        # Long / Short / Netto / Brutto
        longs  = sum(v for p, v in zip(positions, values) if p.direction == "long")
        shorts = sum(v for p, v in zip(positions, values) if p.direction == "short")
        net    = round(longs - shorts, 2)
        gross  = round(longs + shorts, 2)

        total_value = gross  # nur zur Anzeige (entspricht dem Brutto-Exposure)

        cluster_risks = _check_cluster_risks(positions, values, gross)
        alerts: list[str] = [r["message"] for r in cluster_risks]

        # P&L-Alarme — richtungs-bewusst
        for p, cur in zip(positions, cur_prices):
            if p.entry_price > 0:
                if p.direction == "long":
                    pnl = (cur - p.entry_price) / p.entry_price
                else:  # short: Gewinn, wenn der Kurs fällt
                    pnl = (p.entry_price - cur) / p.entry_price
                if pnl < -LOSS_THRESHOLD:
                    alerts.append(
                        f"Offener Verlust {p.ticker} ({p.direction}): {pnl:.0%} "
                        f"(Einstand: {p.entry_price:.2f}, Heute: {cur:.2f})"
                    )

        # Memory-Alignment-Warnungen — richtungs-bewusst:
        #   long  ist fehlausgerichtet, wenn die Analyse raus/drehen will (SELL/SHORT);
        #   short ist fehlausgerichtet, wenn die Analyse eindecken/drehen will (COVER/BUY).
        # Sonst würde ein Short mit letzter Analyse SHORT (= perfekt ausgerichtet)
        # fälschlich gewarnt und ein Short mit COVER (= echte Fehlausrichtung) übersehen.
        for p in positions:
            history = self.memory.load_history(p.ticker, days=90)
            if not history:
                continue
            last_rec = history[0].get("recommendation", "")
            if p.direction == "long":
                misaligned = last_rec in ("SELL", "SHORT")
            else:  # short
                misaligned = last_rec in ("COVER", "BUY")
            if misaligned:
                alerts.append(
                    f"Alignment-Warnung {p.ticker} ({p.direction}): letzte Analyse = {last_rec}, "
                    f"Position aber noch gehalten."
                )

        # Konzentration (HHI) über Brutto-Gewichte
        weights = [v / gross for v in values] if gross > 0 else []
        hhi = _herfindahl(weights)

        # Portfolio-Vola / MaxDD — signierte Gewichte, damit Hedges die Vola senken
        port_vol = 0.0
        port_mdd = 0.0
        if self.returns_provider and gross > 0:
            series = []
            for p, val in zip(positions, values):
                rets = self.returns_provider(p.ticker) or []
                if rets:
                    signed_weight = (val / gross) if p.direction == "long" else -(val / gross)
                    series.append((signed_weight, rets))
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
            "total_positions":         len(positions),
            "total_value_usd":         round(total_value, 2),
            "long_value":              round(longs, 2),
            "short_value":             round(shorts, 2),
            "net_exposure":            net,
            "gross_exposure":          gross,
            "cluster_risks":           cluster_risks,
            "alerts":                  alerts,
            "overall_health":          health,
            "concentration_hhi":       hhi,
            "portfolio_volatility":    port_vol,
            "portfolio_max_drawdown":  port_mdd,
        }

    async def run(self) -> None:
        try:
            positions = self.portfolio_port.get_positions()
        except PortfolioError as e:
            print(f"[PortfolioMonitor] Portfolio-Daten ungültig: {e}")
            return

        if not positions:
            print("[PortfolioMonitor] Keine Positionen erfasst — übersprungen.")
            return

        snapshot = self._evaluate_positions(positions)
        self.memory.save_portfolio_snapshot(snapshot)

        health = snapshot["overall_health"].upper()
        # Netto UND Brutto getrennt ausweisen: bei einem marktneutralen Buch
        # (z. B. 100 long / 100 short) wäre eine einzelne "Wert"-Zeile (= Brutto)
        # irreführend, weil netto ~0 Kapital gebunden ist.
        print(f"[PortfolioMonitor] Gesundheit: {health} | "
              f"{len(snapshot['alerts'])} Warnungen | "
              f"Netto: ${snapshot['net_exposure']:,.0f} | "
              f"Brutto: ${snapshot['gross_exposure']:,.0f}")
        for alert in snapshot["alerts"]:
            print(f"  ⚠ {alert}")
