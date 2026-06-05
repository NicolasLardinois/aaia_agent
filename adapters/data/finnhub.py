"""
FundamentalsProvider implementiert via yfinance + SEC EDGAR + FRED + FMP.

Shiller KGV:
  Stufe 1 (US):    SEC EDGAR (10 Jahre EPS) + FRED CPIAUCSL
  Stufe 2 (EU/CH): FMP (10 Jahre EPS) + FRED HICP/CPI je Region
  Stufe 3 (alle):  yfinance (~4 Jahre, nominal) als letzter Fallback

WACC und ROIC werden aus Bilanzdaten berechnet.
shiller_cape bleibt None nur wenn keine Stufe ausreichend Daten liefert.
"""
import datetime
import json
import os
import urllib.request
from typing import Optional

import requests
import yfinance as yf

from core.ports.data_provider import FundamentalsProvider

# ── SEC EDGAR Ticker→CIK Cache (wird einmalig pro Prozesslauf befüllt) ──────
_SEC_CIK_CACHE: dict[str, Optional[int]] = {}
_SEC_ALL_TICKERS: Optional[dict] = None   # company_tickers.json, einmalig geladen


def _pct(v) -> Optional[float]:
    """Dezimalwert → Prozentwert (0.15 → 15.0)."""
    try:
        f = float(v)
        return round(f * 100, 2) if f == f else None
    except (TypeError, ValueError):
        return None


def _f(v) -> Optional[float]:
    """Sicheres float-Casting; None bei NaN oder Fehler."""
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


# ── SEC EDGAR Hilfsfunktionen ────────────────────────────────────────────────

def _sec_load_tickers() -> dict:
    """Lädt company_tickers.json von SEC (einmalig, gecacht)."""
    global _SEC_ALL_TICKERS
    if _SEC_ALL_TICKERS is not None:
        return _SEC_ALL_TICKERS
    try:
        req = urllib.request.Request(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": "aaia-agent research@aaia.finance"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            _SEC_ALL_TICKERS = json.loads(resp.read())
    except Exception:
        _SEC_ALL_TICKERS = {}
    return _SEC_ALL_TICKERS


def _sec_cik(ticker: str) -> Optional[int]:
    """CIK-Nummer für einen US-Ticker aus dem SEC-Verzeichnis ermitteln."""
    if ticker in _SEC_CIK_CACHE:
        return _SEC_CIK_CACHE[ticker]
    tickers = _sec_load_tickers()
    ticker_upper = ticker.upper()
    cik = None
    for entry in tickers.values():
        if entry.get("ticker", "").upper() == ticker_upper:
            cik = int(entry["cik_str"])
            break
    _SEC_CIK_CACHE[ticker] = cik
    return cik


def _sec_eps_annual(cik: int) -> dict[int, float]:
    """
    Jährlicher diluted EPS aus offiziellen 10-K Einreichungen (SEC EDGAR XBRL).
    Gibt {Jahr: EPS} zurück; spätere Amendments überschreiben frühere.
    """
    try:
        cik_str = str(cik).zfill(10)
        req = urllib.request.Request(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_str}.json",
            headers={"User-Agent": "aaia-agent research@aaia.finance"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            facts = json.loads(resp.read())

        gaap = facts.get("facts", {}).get("us-gaap", {})

        # Bevorzuge diluted, Fallback auf basic
        eps_entries: list = []
        for field in (
            "EarningsPerShareDiluted",
            "EarningsPerShareBasicAndDiluted",
            "EarningsPerShareBasic",
        ):
            entries = gaap.get(field, {}).get("units", {}).get("USD/shares", [])
            if entries:
                eps_entries = entries
                break

        # Sortiert nach Einreichungsdatum → spätere Amendments gewinnen
        annual: dict[int, float] = {}
        for entry in sorted(eps_entries, key=lambda e: e.get("filed", "")):
            if entry.get("form") in ("10-K", "10-K/A") and entry.get("fp") == "FY":
                year = int(entry["end"][:4])
                val  = _f(entry.get("val"))
                if val is not None:
                    annual[year] = val

        return annual
    except Exception:
        return {}


# FRED CPI-Serien je Region
_FRED_CPI_SERIES = {
    "us":        "CPIAUCSL",           # US CPI
    "eurozone":  "CP0000EZ19M086NEST", # Eurozone HICP
    "ch":        "CHECPIALLMINMEI",    # Schweizer CPI
}

_CPI_CACHE: dict[str, dict[int, float]] = {}


def _cpi_annual(region: str = "us") -> dict[int, float]:
    """
    Jährliche CPI-Durchschnittswerte von FRED.
    region: "us" | "eurozone" | "ch"
    Gibt {Jahr: CPI-Durchschnitt} zurück.
    """
    if region in _CPI_CACHE:
        return _CPI_CACHE[region]
    try:
        fred_key = os.getenv("FRED_API_KEY")
        fred_id  = _FRED_CPI_SERIES.get(region, _FRED_CPI_SERIES["us"])
        if not fred_key:
            return {}
        from fredapi import Fred
        series = Fred(api_key=fred_key).get_series(fred_id)
        annual = series.groupby(series.index.year).mean()
        result = {int(yr): float(val) for yr, val in annual.items()
                  if val == val}  # NaN-Filter
        _CPI_CACHE[region] = result
        return result
    except Exception:
        return {}


# ── FMP (Financial Modeling Prep) ────────────────────────────────────────────

_FMP_BASE = "https://financialmodelingprep.com/api/v3"
_FMP_EPS_CACHE: dict[str, dict[int, float]] = {}


def _fmp_eps_annual(ticker: str) -> dict[int, float]:
    """
    10 Jahre jährlicher diluted EPS via FMP Income Statement API.
    Gibt {Jahr: EPS} zurück.
    """
    if ticker in _FMP_EPS_CACHE:
        return _FMP_EPS_CACHE[ticker]
    try:
        api_key = os.getenv("FMP_API_KEY")
        if not api_key:
            return {}
        url  = f"{_FMP_BASE}/income-statement/{ticker}"
        resp = requests.get(url, params={"limit": 12, "apikey": api_key}, timeout=10)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        if not isinstance(data, list):
            return {}
        annual: dict[int, float] = {}
        for entry in data:
            date_str = entry.get("date", "")
            eps      = _f(entry.get("epsDiluted") or entry.get("eps"))
            if date_str and eps is not None:
                year = int(date_str[:4])
                annual[year] = eps
        _FMP_EPS_CACHE[ticker] = annual
        return annual
    except Exception:
        return {}


def _region_from_ticker(ticker: str) -> str:
    """Erkennt Region anhand des Ticker-Suffixes."""
    t = ticker.upper()
    if any(t.endswith(s) for s in (".SW", ".VX")):
        return "ch"
    if any(t.endswith(s) for s in (
        ".PA", ".DE", ".AS", ".BR", ".MI", ".MC",
        ".LS", ".VI", ".HE", ".CO", ".OL", ".ST",
    )):
        return "eurozone"
    return "us"


# ── Shiller KGV ─────────────────────────────────────────────────────────────

def _calc_shiller(price: float, eps_by_year: dict[int, float],
                  cpi_by_year: dict[int, float], current_year: int,
                  min_years: int = 3) -> Optional[float]:
    """Inflationsbereinigtes Shiller KGV aus EPS- und CPI-Daten."""
    cpi_today = cpi_by_year.get(current_year) or cpi_by_year.get(current_year - 1)
    adj_eps: list[float] = []
    for year in range(current_year - 10, current_year):
        eps = eps_by_year.get(year)
        if eps is None or eps <= 0:
            continue
        cpi_year = cpi_by_year.get(year)
        if cpi_today and cpi_year and cpi_year > 0:
            adj_eps.append(eps * (cpi_today / cpi_year))
        else:
            adj_eps.append(eps)
    if len(adj_eps) < min_years:
        return None
    return round(price / (sum(adj_eps) / len(adj_eps)), 2)


def _shiller_cape(info: dict, is_stmt, fin, ticker: str) -> Optional[float]:
    """
    Shiller KGV = aktueller Kurs / inflationsbereinigter Ø-EPS (10 Jahre).

    Stufe 1 (US):    SEC EDGAR (10 Jahre EPS) + FRED CPIAUCSL
    Stufe 2 (EU/CH): FMP (10 Jahre EPS) + FRED HICP/CPI je Region
    Stufe 3 (alle):  yfinance (~4 Jahre, nominal)
    """
    price = _f(info.get("currentPrice")) or _f(info.get("regularMarketPrice"))
    if not price or price <= 0:
        return None

    current_year = datetime.date.today().year
    region       = _region_from_ticker(ticker)

    # ── Stufe 1: SEC EDGAR + FRED (US-Aktien) ────────────────────────────────
    cik = _sec_cik(ticker)
    if cik:
        eps_by_year = _sec_eps_annual(cik)
        if len(eps_by_year) >= 3:
            result = _calc_shiller(price, eps_by_year, _cpi_annual("us"), current_year)
            if result is not None:
                return result

    # ── Stufe 2: FMP + FRED (EU/CH und alle anderen) ─────────────────────────
    fmp_eps = _fmp_eps_annual(ticker)
    if len(fmp_eps) >= 3:
        result = _calc_shiller(price, fmp_eps, _cpi_annual(region), current_year)
        if result is not None:
            return result

    # ── Stufe 3: yfinance Fallback (~4 Jahre, nominal) ───────────────────────
    shares = (_f(info.get("sharesOutstanding"))
              or _f(info.get("impliedSharesOutstanding")))
    if not shares or shares <= 0:
        return None

    for stmt in (is_stmt, fin):
        if stmt is None or stmt.empty:
            continue
        for label in (
            "Net Income",
            "Net Income Applicable To Common Shares",
            "Net Income Common Stockholders",
        ):
            if label not in stmt.index:
                continue
            eps_values = [
                e for ni in stmt.loc[label].dropna()
                if (e := _f(ni / shares)) is not None and e > 0
            ]
            if not eps_values:
                continue
            return round(price / (sum(eps_values) / len(eps_values)), 2)

    return None


# ── Restliche Berechnungsfunktionen ──────────────────────────────────────────

def _tax_rate(is_stmt) -> float:
    """Effektiver Steuersatz aus Income Statement. Fallback: 21% (US)."""
    try:
        if is_stmt is None or is_stmt.empty:
            return 0.21
        for tax_lbl, pretax_lbl in (
            ("Tax Provision", "Pretax Income"),
            ("Income Tax Expense", "Pretax Income"),
        ):
            if tax_lbl in is_stmt.index and pretax_lbl in is_stmt.index:
                tax    = _f(is_stmt.loc[tax_lbl].iloc[0])
                pretax = _f(is_stmt.loc[pretax_lbl].iloc[0])
                if tax is not None and pretax and pretax != 0:
                    return max(0.0, min(0.50, tax / pretax))
    except Exception:
        pass
    return 0.21


def _equity_from_bs(bs) -> Optional[float]:
    for label in ("Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"):
        if label in bs.index:
            return _f(bs.loc[label].iloc[0])
    return None


def _roic(info: dict, bs, is_stmt) -> Optional[float]:
    """ROIC = NOPAT / Invested Capital × 100."""
    try:
        if bs is None or bs.empty:
            return None
        op_income = _f(info.get("operatingIncome"))
        if op_income is None:
            return None
        nopat          = op_income * (1 - _tax_rate(is_stmt))
        equity         = _equity_from_bs(bs)
        if equity is None:
            return None
        total_debt     = _f(info.get("totalDebt")) or 0.0
        cash           = _f(info.get("totalCash")) or 0.0
        inv_capital    = equity + total_debt - cash
        if inv_capital <= 0:
            return None
        return round(nopat / inv_capital * 100, 2)
    except Exception:
        return None


def _wacc(info: dict, is_stmt, risk_free: float = 0.045) -> Optional[float]:
    """WACC = (E/V)×Re + (D/V)×Rd×(1−t). Re per CAPM mit ERP 5.5%."""
    try:
        beta           = _f(info.get("beta")) or 1.0
        cost_of_equity = risk_free + beta * 0.055
        market_cap     = _f(info.get("marketCap"))
        if market_cap is None:
            return None
        total_debt   = _f(info.get("totalDebt")) or 0.0
        interest_exp = _f(info.get("interestExpense"))
        cost_of_debt = (
            min(abs(interest_exp) / total_debt, 0.25)
            if total_debt > 0 and interest_exp is not None
            else risk_free + 0.02
        )
        tax           = _tax_rate(is_stmt)
        total_capital = market_cap + total_debt
        if total_capital <= 0:
            return None
        wacc = (market_cap / total_capital * cost_of_equity
                + total_debt / total_capital * cost_of_debt * (1 - tax))
        return round(wacc * 100, 2)
    except Exception:
        return None


def _revenue_cagr_3y(is_stmt, financials) -> Optional[float]:
    """Echte Umsatz-CAGR über verfügbare Jahre (bis zu 4 Jahresabschlüsse)."""
    for stmt in (is_stmt, financials):
        if stmt is None or stmt.empty:
            continue
        for label in ("Total Revenue", "Revenue"):
            if label not in stmt.index:
                continue
            try:
                rev    = stmt.loc[label].dropna()
                newest = _f(rev.iloc[0])
                oldest = _f(rev.iloc[-1])
                years  = len(rev) - 1
                if newest and oldest and oldest > 0 and years > 0:
                    return round(((newest / oldest) ** (1 / years) - 1) * 100, 2)
            except Exception:
                continue
    return None


def _altman_z(info: dict, bs) -> Optional[float]:
    """Altman Z-Score aus Bilanzdaten."""
    try:
        if bs is None or bs.empty:
            return None
        ta = _f(bs.loc["Total Assets"].iloc[0]) if "Total Assets" in bs.index else None
        if not (ta and ta > 0):
            return None
        re = _f(bs.loc["Retained Earnings"].iloc[0]) if "Retained Earnings" in bs.index else None
        tl = _f(bs.loc["Total Liabilities Net Minority Interest"].iloc[0]) if "Total Liabilities Net Minority Interest" in bs.index else None
        if "Working Capital" in bs.index:
            wc = _f(bs.loc["Working Capital"].iloc[0])
        else:
            ca = _f(bs.loc["Current Assets"].iloc[0]) if "Current Assets" in bs.index else None
            cl = _f(bs.loc["Current Liabilities"].iloc[0]) if "Current Liabilities" in bs.index else None
            wc = (ca - cl) if ca is not None and cl is not None else None
        ebitda  = _f(info.get("ebitda"))
        mktcap  = _f(info.get("marketCap"))
        revenue = _f(info.get("totalRevenue"))
        if not (ebitda and mktcap and revenue and tl):
            return None
        z = (1.2 * (wc or 0) / ta
             + 1.4 * (re or 0) / ta
             + 3.3 * ebitda / ta
             + 0.6 * mktcap / (tl or 1)
             + 1.0 * revenue / ta)
        return round(z, 2)
    except Exception:
        return None


# ── Provider ─────────────────────────────────────────────────────────────────

class FinnhubProvider(FundamentalsProvider):

    def __init__(self, api_key: str):
        self.api_key = api_key  # für spätere Finnhub-Integration reserviert

    def get_fundamentals(self, ticker: str) -> dict:
        t       = yf.Ticker(ticker)
        info    = t.info
        bs      = t.balance_sheet
        is_stmt = t.income_stmt
        fin     = t.financials

        market_cap = _f(info.get("marketCap"))
        fcf        = _f(info.get("freeCashflow"))
        revenue    = _f(info.get("totalRevenue"))
        ebitda     = _f(info.get("ebitda"))
        total_debt = _f(info.get("totalDebt")) or 0.0
        cash       = _f(info.get("totalCash")) or 0.0

        price_fcf       = round(market_cap / fcf, 2) if market_cap and fcf and fcf > 0 else None
        fcf_margin      = round(fcf / revenue * 100, 2) if fcf and revenue and revenue > 0 else None
        net_debt        = total_debt - cash
        net_debt_ebitda = round(net_debt / ebitda, 2) if ebitda and ebitda != 0 else None

        op_income    = _f(info.get("operatingIncome"))
        interest_exp = _f(info.get("interestExpense"))
        interest_coverage = (
            round(op_income / abs(interest_exp), 2)
            if op_income is not None and interest_exp and interest_exp != 0 else None
        )

        dte_raw = _f(info.get("debtToEquity"))
        dte = round(dte_raw / 100, 4) if dte_raw is not None else None

        return {
            "pe_ratio":          _f(info.get("trailingPE")),
            "forward_pe":        _f(info.get("forwardPE")),
            "shiller_cape":      _shiller_cape(info, is_stmt, fin, ticker),
            "peg_ratio":         _f(info.get("pegRatio")),
            "ev_ebitda":         _f(info.get("enterpriseToEbitda")),
            "ev_revenue":        _f(info.get("enterpriseToRevenue")),
            "price_book":        _f(info.get("priceToBook")),
            "price_sales":       _f(info.get("priceToSalesTrailing12Months")),
            "price_fcf":         price_fcf,
            "dividend_yield":    _pct(info.get("dividendYield")),
            "wacc":              _wacc(info, is_stmt),
            "revenue_cagr_3y":   _revenue_cagr_3y(is_stmt, fin),
            "operating_margin":  _pct(info.get("operatingMargins")),
            "gross_margin":      _pct(info.get("grossMargins")),
            "net_margin":        _pct(info.get("profitMargins")),
            "fcf_margin":        fcf_margin,
            "debt_to_equity":    dte,
            "roe":               _pct(info.get("returnOnEquity")),
            "roa":               _pct(info.get("returnOnAssets")),
            "roic":              _roic(info, bs, is_stmt),
            "net_debt_ebitda":   net_debt_ebitda,
            "interest_coverage": interest_coverage,
            "current_ratio":     _f(info.get("currentRatio")),
            "altman_z":          _altman_z(info, bs),
        }

    def get_short_interest(self, ticker: str) -> dict:
        info      = yf.Ticker(ticker).info
        short_pct = _f(info.get("shortPercentOfFloat"))
        return {
            "short_float_pct": round(short_pct * 100, 2) if short_pct is not None else None,
            "days_to_cover":   _f(info.get("shortRatio")),
        }

    def get_insider_activity(self, ticker: str) -> list[dict]:
        try:
            df = yf.Ticker(ticker).insider_transactions
            if df is None or df.empty:
                return []
            result = []
            for _, row in df.iterrows():
                text = str(row.get("Text", "")).lower()
                if any(w in text for w in ("purchase", "acquisition")):
                    result.append({"type": "buy"})
                elif any(w in text for w in ("sale", "disposition")):
                    result.append({"type": "sell"})
            return result
        except Exception:
            return []

    def get_earnings_history(self, ticker: str) -> list[dict]:
        try:
            df = yf.Ticker(ticker).earnings_history
            if df is None or df.empty:
                return []
            result = []
            for _, row in df.iterrows():
                estimate = _f(row.get("EPS Estimate"))
                reported = _f(row.get("Reported EPS"))
                if estimate is None or reported is None:
                    continue
                result.append({
                    "beat":     bool(reported > estimate),
                    "revision": 0.0,
                })
            return result[-8:]
        except Exception:
            return []

    def get_bond_data(self, ticker: str) -> dict:
        # Anleihe-spezifische Daten (Kupon, Laufzeit, YTM) nicht via yfinance verfügbar
        return {}
