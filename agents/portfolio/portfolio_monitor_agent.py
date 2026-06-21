import asyncio
from typing import Callable, Optional

import pandas as pd
import yfinance as yf

from core.domain.portfolio import Position, PortfolioError
from core.ports.data_provider import MarketDataProvider
from core.ports.memory_port import MemoryPort
from core.ports.portfolio_port import PortfolioPort
from core.utils.performance_metrics import max_drawdown

SECTOR_THRESHOLD      = 0.40
ASSET_CLASS_THRESHOLD = 0.60   # verschärft von 0.80
COUNTRY_THRESHOLD     = 0.70
LOSS_THRESHOLD        = 0.15
BASE_CURRENCY         = "USD"


def make_returns_provider(market_provider):
    """Callable ticker -> datierte Renditereihe (pandas Series, nach Datum indiziert) aus
    get_price_history (Close → pct_change). Die Datums-Indizierung ist wesentlich: die Vola
    führt die Renditen mehrerer Titel PER DATUM zusammen (gemeinsamer Handelskalender), nicht
    per Listenposition — sonst würden unterschiedlich lange/verschobene Reihen (z. B. wegen
    US/CH/EU-Feiertagen) falsch übereinandergelegt. Fehler → leere Series."""
    def _provider(ticker: str) -> "pd.Series":
        try:
            hist = market_provider.get_price_history(ticker, "1y")
            close = hist["Close"].dropna()
            return close.pct_change().dropna()
        except Exception:
            return pd.Series(dtype=float)
    return _provider


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


_US = {"USA", "US", "United States"}
_CH = {"CH", "CHE", "Schweiz", "Switzerland"}
_EUROZONE = {
    "DE", "FR", "IT", "ES", "NL", "AT", "BE", "PT", "FI", "IE", "GR", "SK", "SI",
    "EE", "LV", "LT", "LU", "MT", "CY",
    "Deutschland", "Frankreich", "Eurozone",
}

# Anlageklassen, die ins net_beta einfließen: nur Aktien/Indizes. net_beta dimensioniert
# einen AKTIEN-Index-Hedge (Track B), der nur Aktien-Exposure absichern kann. Bonds,
# Rohstoffe und Edelmetalle haben kein Aktienmarkt-Beta (eine Anleihe ≠ Aktie) → sie
# gehören nicht in die Zahl; ihr Risiko fängt die Portfolio-Vola ab (komplementär).
_EQUITY_CLASSES = {"equity", "index"}


def _region_of(country: str) -> str:
    c = (country or "").strip()
    if c in _US:
        return "USA"
    if c in _CH:
        return "CH"
    if c in _EUROZONE:
        return "Eurozone"
    return c or "Unbekannt"


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
        market_provider: Optional[MarketDataProvider] = None,
        fx_rate: Callable[[str, str], float] = _default_fx_rate,
        # returns_provider liefert je Ticker eine Renditereihe (datierte pd.Series oder Liste);
        # siehe make_returns_provider.
        returns_provider: Optional[Callable[[str], object]] = None,
    ):
        self.memory = memory
        self.portfolio_port = portfolio_port
        self.market_provider = market_provider
        self.fx_rate = fx_rate
        self.returns_provider = returns_provider

    def _beta_for(self, ticker: str) -> float:
        if self.market_provider is None:
            return 1.0
        try:
            info = self.market_provider.get_info(ticker) or {}
            b = info.get("beta")
            return float(b) if b is not None else 1.0
        except Exception:
            return 1.0

    async def _gather_market_data(self, positions: list[Position]) -> dict[int, dict]:
        """Holt je Position Kurs, Beta und Renditen PARALLEL: das blockierende yfinance-I/O
        (fast_info, get_info=.info, get_price_history) läuft in Threads (asyncio.to_thread)
        und alle Positionen nebenläufig (asyncio.gather). Sonst liefen die Calls je Position
        streng sequenziell und könnten in Yahoos Rate-Limit laufen (AGENTS.md §2)."""
        async def _one(p: Position) -> dict:
            price = await asyncio.to_thread(
                lambda: p.current_price if p.current_price is not None
                else (_fetch_current_price(p.ticker) or p.entry_price)
            )
            beta = await asyncio.to_thread(self._beta_for, p.ticker)
            rets = (await asyncio.to_thread(self.returns_provider, p.ticker)
                    if self.returns_provider else None)
            return {"price": price, "beta": beta, "returns": rets}

        results = await asyncio.gather(*[_one(p) for p in positions])
        return {i: r for i, r in enumerate(results)}

    def _evaluate_positions(
        self, positions: list[Position], market_data: Optional[dict[int, dict]] = None,
    ) -> dict:
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
                "net_beta":                {},
                "net_beta_pct":            {},
                "bond_risk_affinities":    [],
            }

        # Datenzugriff je Position: vorab parallel geholte Werte (market_data) bevorzugen,
        # sonst synchron nachladen (Fallback — hält Direkt-Aufrufe ohne Prefetch testbar).
        def _price(i: int, p: Position) -> float:
            if market_data is not None:
                return market_data[i]["price"]
            return p.current_price if p.current_price is not None else (_fetch_current_price(p.ticker) or p.entry_price)

        def _beta(i: int, p: Position) -> float:
            if market_data is not None:
                return market_data[i]["beta"]
            return self._beta_for(p.ticker)

        def _returns(i: int, p: Position):
            if market_data is not None:
                return market_data[i]["returns"]
            return self.returns_provider(p.ticker) if self.returns_provider else None

        # Aktuellen Kurs ermitteln und Positionswert in Basiswährung berechnen
        values: list[float] = []
        cur_prices: list[float] = []
        for i, p in enumerate(positions):
            cur = _price(i, p)
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

        # Memory-Alignment-Warnungen — richtungs-bewusst UND an die je Linse persistierte Aktion gekoppelt:
        #   long  liest die Long-Aktion (Feld "recommendation") → Fehlausrichtung = SELL (Analyse will raus);
        #   short liest die Short-Aktion (Feld "short_action")   → Fehlausrichtung = COVER (Engine will eindecken).
        # Wichtig: die Long-Linse deferiert bei Short-Positionen auf NONE, daher MUSS die Short-Warnung
        # am separat persistierten short_action hängen — am recommendation-Feld stünde für Shorts immer NONE.
        for p in positions:
            history = self.memory.load_history(p.ticker, days=90)
            if not history:
                continue
            last = history[0]
            if p.direction == "long":
                last_action = last.get("recommendation", "")
                misaligned = last_action == "SELL"
            else:  # short
                last_action = last.get("short_action", "")
                misaligned = last_action == "COVER"
            if misaligned:
                alerts.append(
                    f"Alignment-Warnung {p.ticker} ({p.direction}): letzte Analyse = {last_action}, "
                    f"Position aber noch gehalten."
                )

        # Konzentration (HHI) über Brutto-Gewichte
        weights = [v / gross for v in values] if gross > 0 else []
        hhi = _herfindahl(weights)

        # Portfolio-Vola / MaxDD — signierte Gewichte, damit Hedges die Vola senken.
        # Renditen werden PER DATUM zusammengeführt (Index-Schnitt via DataFrame.dropna),
        # nicht per Listenposition — sonst würden Titel mit unterschiedlich langer/verschobener
        # Historie (z. B. wegen US/CH/EU-Feiertagen) falsch übereinandergelegt. Die
        # pd.Series-Coercion lässt auch reine Listen zu (dann Positions-Alignment).
        port_vol = 0.0
        port_mdd = 0.0
        if self.returns_provider and gross > 0:
            cols: dict[int, pd.Series] = {}
            col_weights: dict[int, float] = {}
            for i, (p, val) in enumerate(zip(positions, values)):
                raw = _returns(i, p)
                if raw is None:
                    continue
                s = pd.Series(raw)
                if s.empty:
                    continue
                cols[i] = s
                col_weights[i] = (val / gross) if p.direction == "long" else -(val / gross)
            if cols:
                # dropna() = innerer Join: nur Tage, die ALLE Titel gemeinsam haben.
                aligned = pd.DataFrame(cols).dropna()
                if not aligned.empty:
                    w = pd.Series(col_weights)
                    port_returns = aligned.mul(w, axis=1).sum(axis=1).tolist()
                    if len(port_returns) >= 2:
                        mean = sum(port_returns) / len(port_returns)
                        var = sum((x - mean) ** 2 for x in port_returns) / (len(port_returns) - 1)
                        port_vol = round(var ** 0.5, 4)
                    port_mdd = round(max_drawdown(port_returns), 4)

        n_alerts = len(alerts)
        health   = "green" if n_alerts == 0 else ("yellow" if n_alerts <= 2 else "red")

        # net_beta pro Region: Σ(signed_value · β) je Markt (USD-Betrag) — NUR Aktien/Indizes
        # (siehe _EQUITY_CLASSES; Bonds/Rohstoffe/Edelmetalle haben kein Aktienmarkt-Beta).
        net_beta: dict[str, float] = {}
        equity_gross: dict[str, float] = {}   # je Region das Aktien-Brutto (Nenner für net_beta_pct)
        for i, (p, val) in enumerate(zip(positions, values)):
            if p.asset_class not in _EQUITY_CLASSES:
                continue
            signed = val if p.direction == "long" else -val
            region = _region_of(p.country)
            net_beta[region] = net_beta.get(region, 0.0) + signed * _beta(i, p)
            equity_gross[region] = equity_gross.get(region, 0.0) + val
        net_beta = {r: round(v, 2) for r, v in net_beta.items()}
        # net_beta_pct: beta-gewichtete Aktien-Netto-Exposure relativ zum AKTIEN-Brutto DERSELBEN
        # Region (Äpfel mit Äpfeln). Achtung Mischgröße: Zähler ist beta-gewichtet, der Nenner
        # nicht → bei β>1 kann |net_beta_pct| über 100 % liegen. Nicht-Aktien zählen weder im
        # Zähler noch im Nenner (konsistent zu net_beta).
        net_beta_pct = {
            r: round(net_beta[r] / equity_gross[r], 3)
            for r in net_beta if equity_gross.get(r, 0.0) > 0
        }

        bond_risk_affinities = [
            {"ticker": p.ticker, "risk_affinity": p.risk_affinity}
            for p in positions if p.asset_class == "bond" and p.risk_affinity is not None
        ]

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
            "net_beta":                net_beta,
            "net_beta_pct":            net_beta_pct,
            "bond_risk_affinities":    bond_risk_affinities,
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

        # Markt-Daten (Kurs/Beta/Renditen) je Position parallel vorab holen, dann rein
        # rechnen — so blockiert das yfinance-I/O nicht sequenziell (AGENTS.md §2).
        market_data = await self._gather_market_data(positions)
        snapshot = self._evaluate_positions(positions, market_data)
        self.memory.save_portfolio_snapshot(snapshot)

        health = snapshot["overall_health"].upper()
        # Netto UND Brutto getrennt ausweisen: bei einem marktneutralen Buch
        # (z. B. 100 long / 100 short) wäre eine einzelne "Wert"-Zeile (= Brutto)
        # irreführend, weil netto ~0 Kapital gebunden ist.
        print(f"[PortfolioMonitor] Gesundheit: {health} | "
              f"{len(snapshot['alerts'])} Warnungen | "
              f"Netto: ${snapshot['net_exposure']:,.0f} | "
              f"Brutto: ${snapshot['gross_exposure']:,.0f}")
        for region, v in (snapshot.get("net_beta") or {}).items():
            pct = (snapshot.get("net_beta_pct") or {}).get(region)
            suffix = f" ({pct:+.0%} Brutto)" if pct is not None else ""
            print(f"  net-β {region}: ${v:,.0f}{suffix}")
        for e in snapshot.get("bond_risk_affinities", []):
            print(f"  Anleihe {e['ticker']}: Risikoaffinität = {e['risk_affinity']}")
        for alert in snapshot["alerts"]:
            print(f"  ⚠ {alert}")
