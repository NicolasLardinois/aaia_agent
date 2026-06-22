"""Regime-Replay-Backtest (Stufe 1).
Verwendung:
  python -m app.replay_regime [--start YYYY-MM] [--end YYYY-MM]
Schreibt data/backtests/regime_replay_YYYYMMDD.json + .md."""
import argparse
import json
import os
from collections import Counter
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
import yfinance as yf
from fredapi import Fred

from config.settings import FRED_API_KEY
from adapters.data.historical_fred import HistoricalFredProvider
from agents.backtester.regime_replay import run_replay
from core.utils.backtest import benchmark_for_market
from core.utils.regime_eval import evaluate_market, evaluate_nber, build_report_md

_HORIZONS = (3, 6, 12)
# v1-Entrypoint läuft USA. Region-Steckbarkeit liegt in der Library-API (run_replay nimmt
# ecb_factory/snb_factory; evaluate_market nimmt die Kursfunktion injiziert; Benchmark über
# benchmark_for_market). EU/CH-Entrypoint = Stufe ①b (Spec §4.4/§10).
_REGION = "USA"


def _monatsenden(start: date, end: date) -> list:
    out, cur = [], start
    while cur <= end:
        out.append(cur)
        cur = cur + relativedelta(months=1)
    return out


def _price_on(ticker: str, d: date):
    """Erster Benchmark-Schlusskurs am/nach d. None = kein Kurs."""
    try:
        df = yf.Ticker(ticker).history(start=d.strftime("%Y-%m-%d"), period="10d")
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[0])
    except Exception:
        return None


def _usrec_by_month(fred: Fred) -> dict:
    s = fred.get_series("USREC").dropna()
    return {f"{ts.year:04d}-{ts.month:02d}": int(v) for ts, v in s.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="1960-01")
    ap.add_argument("--end", default=date.today().strftime("%Y-%m"))
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m").date().replace(day=1)
    end = datetime.strptime(args.end, "%Y-%m").date().replace(day=1)
    stichtage = _monatsenden(start, end)

    print(f"[RegimeReplay] {len(stichtage)} Stichtage {args.start}..{args.end} (Region {_REGION}) …")
    urteile = run_replay(lambda d: HistoricalFredProvider(FRED_API_KEY, d), stichtage)

    # (A) Markt-Wahrheit: Benchmark region-abhängig via benchmark_for_market (USA→^GSPC).
    benchmark = benchmark_for_market(_REGION)
    market = evaluate_market(urteile, lambda d: _price_on(benchmark, d), horizons_months=_HORIZONS)

    # (B) Wirtschafts-Wahrheit: NBER ist USA-only (Spec §4.4). Andere Regionen: kein Label (Stufe ①b).
    fred = Fred(api_key=FRED_API_KEY)
    nber = evaluate_nber(urteile, _usrec_by_month(fred))
    quality_counts = dict(Counter(u["data_quality"] for u in urteile))
    window = f"{args.start}..{args.end} ({_REGION})"
    md = build_report_md(market, nber, len(urteile), window, quality_counts)

    os.makedirs("data/backtests", exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    payload = {
        "window": window,
        "n_judgments": len(urteile),
        "quality_counts": quality_counts,
        "market": market,
        "nber": nber,
        "judgments": [
            {"as_of": u["as_of"].isoformat(), "regime": u["regime"].value,
             "confidence": u["confidence"], "composite": u["composite"],
             "data_quality": u["data_quality"]}
            for u in urteile
        ],
    }
    with open(f"data/backtests/regime_replay_{stamp}.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(f"data/backtests/regime_replay_{stamp}.md", "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    print(f"\n[RegimeReplay] Report → data/backtests/regime_replay_{stamp}.(json|md)")


if __name__ == "__main__":
    main()
