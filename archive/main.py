"""
main.py — Haupt-Agentenschleife
================================
Verbindet alle 10 Erweiterungen zum vollständigen Multi-Agenten-System.
Lecture-Bezug: Slide 36 (Agent Loop), Slide 48 (Multi-Agent), Slide 50 (Memory)
"""

import os
import time
from dotenv import load_dotenv

from sensors       import EconomicSensor
from phase_detector import PhaseDetector
from weights       import compute_utility
from confidence    import ConfidenceCalculator
from memory        import AgentMemory
from orchestrator  import Orchestrator
from anomaly       import AnomalyDetector
from backtester    import Backtester
from explainer     import Explainer
from portfolio     import PortfolioAllocator

load_dotenv()

FRED_API_KEY  = os.getenv("FRED_API_KEY", "")
LOOP_INTERVAL = 60 * 60   # 1 Stunde (in Sekunden)
MAX_ITERATIONS = None      # None = Endlosschleife


def run_agent_loop(max_iter: int | None = MAX_ITERATIONS) -> None:
    print("=" * 60)
    print("  AAIA — Adaptive AI Investment Agent")
    print("  Multi-Agenten Wirtschafts-Entscheidungssystem")
    print("=" * 60)

    # Komponenten initialisieren
    sensor      = EconomicSensor(FRED_API_KEY)
    detector    = PhaseDetector()
    calculator  = ConfidenceCalculator()
    memory      = AgentMemory()
    orchestrator = Orchestrator()
    anomaly_det = AnomalyDetector()
    backtester  = Backtester()
    explainer   = Explainer()
    allocator   = PortfolioAllocator()

    iteration = 0

    while max_iter is None or iteration < max_iter:
        iteration += 1
        print(f"\n{'─' * 60}")
        print(f"  Iteration {iteration}  |  {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'─' * 60}")

        # ── Schritt 1: Sensoren — aktuelle Daten holen ─────────────────
        print("\n[1] Sensoren: Wirtschaftsdaten von FRED API laden...")
        try:
            state, raw = sensor.get_state()
        except Exception as e:
            print(f"    FEHLER beim Datenabruf: {e}")
            time.sleep(30)
            continue

        for key, val in state.items():
            print(f"    {key:<25} = {val}")

        # ── Schritt 2: Prädiktive Sensoren (Erweiterung 4) ─────────────
        print("\n[2] Prognose: Trendextrapolation 3 Monate voraus...")
        predictions = sensor.predict_state(raw, months_ahead=3)
        volatility  = sensor.get_volatility(raw)
        for key, pred in predictions.items():
            print(f"    {key:<25} → {pred}  (Volatilität: {volatility.get(key, '?')})")

        # ── Schritt 3: Phasenerkennung (Erweiterung 2) ─────────────────
        print("\n[3] Phasenerkennung...")
        phase, phase_conf, evidence = detector.detect(state)
        print(f"    Erkannte Phase : {phase}")
        print(f"    Konfidenz      : {phase_conf:.1%}")

        # ── Schritt 4: Anomalie-Erkennung (Erweiterung 9) ──────────────
        print("\n[4] Anomalie-Erkennung...")
        history = memory._data
        is_anomaly, anomalies = anomaly_det.check(state, history)
        if is_anomaly:
            print(f"    ⚠  {len(anomalies)} Anomalie(n) erkannt:")
            for a in anomalies:
                print(f"       {a['indicator']}: Z={a['z_score']}  ({a['direction']})")
        else:
            print("    Keine Anomalien erkannt.")

        # ── Schritt 5: Ähnliche Situationen aus dem Gedächtnis ─────────
        print("\n[5] Gedächtnis: ähnliche Situationen suchen...")
        similar = memory.find_similar_situations(state)
        if similar:
            print(f"    {len(similar)} ähnliche Situation(en) gefunden:")
            for s in similar:
                print(f"       {s['timestamp'][:10]} | Phase: {s['phase']} | Entscheidung: {s['decision']}")
        else:
            print("    Kein Gedächtnis verfügbar.")

        # ── Schritt 6: Multi-Agenten Konsolidierung (Erweiterung 8) ────
        print("\n[6] Multi-Agenten-System: Abstimmung...")
        final_scores, agent_votes = orchestrator.consolidate(state, phase)
        for agent_name, votes in agent_votes.items():
            best = max(votes, key=votes.get)
            print(f"    {agent_name:<16} → {best}")
        print(f"    Konsolidierte Scores: {final_scores}")

        # ── Schritt 7: Konfidenz (Erweiterung 6) ───────────────────────
        print("\n[7] Konfidenzberechnung...")
        confidence, conf_breakdown = calculator.compute(final_scores, volatility, phase_conf)
        sufficient = calculator.is_sufficient(confidence, final_scores)
        print(f"    Gesamtkonfidenz: {confidence:.1%}  ({'ausreichend' if sufficient else 'zu niedrig'})")
        print(f"    Score-Gap: {conf_breakdown['score_gap']:.4f}  |  Vol-Konf: {conf_breakdown['vol_confidence']:.2f}")

        # ── Schritt 8: Portfolio-Allokation (Erweiterung 1) ────────────
        print("\n[8] Softmax-Portfolioallokation...")
        allocation = allocator.allocate(final_scores, confidence, sufficient)
        decision   = allocator.best_portfolio(allocation)
        for portfolio, pct in allocation.items():
            bar = "█" * int(pct * 20)
            print(f"    {portfolio:<10} {pct:>6.1%}  {bar}")
        print(f"    Hauptempfehlung: {decision}")

        # ── Schritt 9: Backtesting / Selbst-Evaluation (Erweiterung 7) ─
        print("\n[9] Backtesting (Selbst-Evaluation)...")
        backtest = backtester.evaluate(memory._data, decision, final_scores)
        if backtest.get("accuracy") is not None:
            print(f"    Genauigkeit vergangener Entscheidungen: {backtest['accuracy']:.1%}")
            print(f"    Status: {backtest['status']}")
            print(f"    → {backtest['recommendation']}")
        else:
            print(f"    {backtest['status']}")

        # ── Schritt 10: Erklärbarkeit (Erweiterung 10) ─────────────────
        print("\n[10] Erklärbarkeit (XAI)...")
        explanation = explainer.explain(state, phase, decision, agent_votes)
        print(f"    {explanation['summary']}")
        print("    Top-3 Einflussfaktoren:")
        for factor, info in explanation["top_factors"].items():
            print(f"      {factor:<25} Beitrag: {info['contribution']:+.4f}")

        # ── Gedächtnis speichern ────────────────────────────────────────
        memory.record(state, phase, decision, final_scores, confidence, allocation)
        print(f"\n    Entscheidung in Gedächtnis gespeichert ({memory.summary()})")

        print(f"\n  Nächste Prüfung in {LOOP_INTERVAL // 60} Minuten...")
        time.sleep(LOOP_INTERVAL)


if __name__ == "__main__":
    if not FRED_API_KEY:
        print("FEHLER: FRED_API_KEY nicht gesetzt.")
        print("Bitte .env.example zu .env kopieren und API-Key eintragen.")
        print("Kostenloser Key: https://fred.stlouisfed.org/docs/api/api_key.html")
    else:
        run_agent_loop()
