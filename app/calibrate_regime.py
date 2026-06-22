"""Regime-Kalibrierung (Stufe ②-v1) — schlägt einen Risk-off-Grenz-Bias vor (kein Auto-Apply).
Verwendung:
  python -m app.calibrate_regime [--start YYYY-MM] [--end YYYY-MM] [--folds N]
Schreibt data/backtests/regime_calib_YYYYMMDD.(json|md)."""
import argparse
import json
import os
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
import yfinance as yf
from fredapi import Fred

from config.settings import FRED_API_KEY
from adapters.data.historical_fred import HistoricalFredProvider
from adapters.data.ecb_snb_stub import EcbStubProvider, SnbStubProvider
from agents.backtester.regime_replay import run_replay
from core.utils.backtest import benchmark_for_market
from core.utils.regime_calibration import calibrate, build_calib_report_md

_REGION = "USA"   # v1: USA (Composition-Root; Region-Steckbarkeit wie in ①)


def _monatserste(start: date, end: date) -> list:
    """Erzeugt eine Liste aller Monatsersten zwischen start und end (inkl.)."""
    out, cur = [], start
    while cur <= end:
        out.append(cur)
        cur = cur + relativedelta(months=1)
    return out


def _price_on(ticker: str, d: date):
    """Schlusskurs des Tickers am nächsten verfügbaren Handelstag ab d (max. 10 Tage voraus).
    Gibt None zurück wenn kein Kurs verfügbar (Wochenende, Feiertag, Datenlücke)."""
    try:
        df = yf.Ticker(ticker).history(
            start=d.strftime("%Y-%m-%d"), end=(d + timedelta(days=10)).strftime("%Y-%m-%d"))
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[0])
    except Exception:
        return None


def _usrec_by_month(fred: Fred) -> dict:
    """Lädt NBER-Rezessionsindikator (USREC) von FRED: 1 = Rezession, 0 = Expansion.
    Gibt ein Dict {YYYY-MM: int} zurück."""
    s = fred.get_series("USREC").dropna()
    return {f"{ts.year:04d}-{ts.month:02d}": int(v) for ts, v in s.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="1960-01")
    ap.add_argument("--end", default=date.today().strftime("%Y-%m"))
    ap.add_argument("--folds", type=int, default=4)
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m").date().replace(day=1)
    end = datetime.strptime(args.end, "%Y-%m").date().replace(day=1)
    stichtage = _monatserste(start, end)

    print(f"[RegimeCalib] {len(stichtage)} Stichtage {args.start}..{args.end}, {args.folds} Folds …")
    urteile = run_replay(
        lambda d: HistoricalFredProvider(FRED_API_KEY, d), stichtage,
        ecb_factory=lambda d: EcbStubProvider(), snb_factory=lambda d: SnbStubProvider())
    records = [(u["as_of"], u["composite"], u["trend"]) for u in urteile]

    fred = Fred(api_key=FRED_API_KEY)
    usrec = _usrec_by_month(fred)
    benchmark = benchmark_for_market(_REGION)
    report = calibrate(records, usrec, sp_price_on=lambda d: _price_on(benchmark, d),
                       folds=args.folds)
    md = build_calib_report_md(report)

    os.makedirs("data/backtests", exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    with open(f"data/backtests/regime_calib_{stamp}.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    with open(f"data/backtests/regime_calib_{stamp}.md", "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    print(f"\n[RegimeCalib] Report → data/backtests/regime_calib_{stamp}.(json|md)")


if __name__ == "__main__":
    main()
