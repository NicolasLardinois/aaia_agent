# Confidence, Memory, Backtester, Anomalie, Portfolio, XAI — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sechs neue Features in das bestehende Multi-Agenten-Finanzsystem integrieren: Anomalie-Erkennung, dynamische Konfidenz mit Cash-Bias, XAI-Erklärungen, persistentes Memory via Supabase/PostgreSQL, drei Backtester-Agenten, und Portfolio-Monitor.

**Architecture:** Direkte Integration in bestehende Orchestratoren (EDA + Hexagonal). Neuer Hexagonal-Port `MemoryPort` mit `SupabaseMemory`-Adapter. Separater `background_runner.py` für tägliche Hintergrundaufgaben via Windows Task Scheduler. Drei Phasen: Foundation → Analyse-Erweiterungen → Hintergrundsystem.

**Tech Stack:** Python 3.11+, Supabase (PostgreSQL), psycopg2-binary, yfinance, bestehende FRED/Yahoo-Finance-Adapter, pytest + unittest.mock

---

## Dateiübersicht

**Neu erstellen:**
```
core/utils/__init__.py
core/utils/statistics.py
core/ports/memory_port.py
adapters/memory/__init__.py
adapters/memory/supabase_memory.py
agents/anomaly/__init__.py
agents/anomaly/top_down_anomaly_agent.py
agents/anomaly/bottom_up_anomaly_agent.py
agents/portfolio/__init__.py
agents/portfolio/portfolio_monitor_agent.py
agents/backtester/__init__.py
agents/backtester/top_down_backtester_agent.py
agents/backtester/bottom_up_backtester_agent.py
agents/backtester/judgment_backtester_agent.py
data/portfolio.json
background_runner.py
tests/__init__.py
tests/test_statistics.py
tests/test_anomaly_agents.py
tests/test_confidence.py
tests/test_portfolio_monitor.py
tests/test_backtester_agents.py
```

**Bestehende Dateien anpassen:**
```
core/domain/models.py                    (AnomalyReport + DeepDiveResult-Felder)
core/domain/recommendation.py           (confidence-Parameter, Cash-Bias)
agents/judgment/judgment_agent.py        (neue Inputs, Confidence-Rechnung, XAI)
orchestrators/judgment_orchestrator.py  (Anomalie-Agenten + Memory-Calls)
requirements.txt
.env.example
```

---

## PHASE 1 — Foundation (Supabase, Domain, Memory)

---

### Task 1: Supabase-Tabellen + Umgebung einrichten

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Schritt 1: Supabase-Projekt erstellen**

  Gehe auf https://supabase.com → "New Project" → Projektname: `aaia-agent` → Region: Europe (Frankfurt) → Passwort notieren.

  Nach dem Erstellen: Settings → Database → Connection string → **URI** kopieren.
  Sieht so aus: `postgresql://postgres:[DEIN-PASSWORT]@db.[PROJEKT-ID].supabase.co:5432/postgres`

- [ ] **Schritt 2: Drei Tabellen im Supabase SQL-Editor erstellen**

  Supabase Dashboard → SQL Editor → "New query" → folgenden SQL einfügen und ausführen:

  ```sql
  CREATE EXTENSION IF NOT EXISTS "pgcrypto";

  CREATE TABLE analysis_memory (
      id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      timestamp        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      ticker           VARCHAR(20) NOT NULL,
      asset_class      VARCHAR(30) NOT NULL,
      market           VARCHAR(10) NOT NULL,
      regime           VARCHAR(20),
      regime_confidence FLOAT,
      top_down_context TEXT,
      alignment        VARCHAR(30),
      dominant_signal  VARCHAR(10),
      recommendation   VARCHAR(10),
      confidence       FLOAT,
      xai_explanation  TEXT,
      price_at_analysis FLOAT,
      top_down_anomaly_severity VARCHAR(10) DEFAULT 'none',
      bottom_up_anomaly_severity VARCHAR(10) DEFAULT 'none',
      indicators_snapshot JSONB DEFAULT '{}'
  );

  CREATE TABLE backtester_reports (
      id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      timestamp               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      backtester_type         VARCHAR(20) NOT NULL,
      ticker                  VARCHAR(20),
      original_recommendation VARCHAR(10),
      price_at_recommendation FLOAT,
      price_today             FLOAT,
      return_pct              FLOAT,
      verdict                 VARCHAR(15),
      accuracy_30d            FLOAT,
      accuracy_60d            FLOAT,
      accuracy_90d            FLOAT,
      notes                   TEXT
  );

  CREATE TABLE portfolio_snapshots (
      id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      total_positions INT,
      total_value_usd FLOAT,
      cluster_risks   JSONB DEFAULT '[]',
      alerts          JSONB DEFAULT '[]',
      overall_health  VARCHAR(10)
  );
  ```

  Erwartete Ausgabe: `Success. No rows returned.`

- [ ] **Schritt 3: requirements.txt ergänzen**

  ```
  fredapi
  pandas
  numpy
  scipy
  plotly
  python-dotenv
  psycopg2-binary
  yfinance
  ```

- [ ] **Schritt 4: .env.example ergänzen**

  ```
  # FRED API — kostenlos: https://fred.stlouisfed.org/docs/api/api_key.html
  FRED_API_KEY=dein_fred_key_hier

  # Anthropic API — https://console.anthropic.com
  ANTHROPIC_API_KEY=dein_anthropic_key_hier

  # Finnhub API — kostenlos: https://finnhub.io
  FINNHUB_API_KEY=dein_finnhub_key_hier

  # Supabase PostgreSQL — Settings → Database → Connection string → URI
  SUPABASE_DB_URL=postgresql://postgres:[PASSWORT]@db.[PROJEKT-ID].supabase.co:5432/postgres
  ```

- [ ] **Schritt 5: Eigene .env ergänzen**

  In `C:\Users\nicil\aaia_agent\.env` die Zeile hinzufügen:
  ```
  SUPABASE_DB_URL=postgresql://postgres:[dein-passwort]@db.[dein-projekt-id].supabase.co:5432/postgres
  ```

- [ ] **Schritt 6: Verbindung testen**

  ```bash
  python -c "
  import os; from dotenv import load_dotenv; load_dotenv()
  import psycopg2
  conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
  cur = conn.cursor()
  cur.execute('SELECT COUNT(*) FROM analysis_memory')
  print('Verbindung OK, Einträge:', cur.fetchone()[0])
  conn.close()
  "
  ```

  Erwartete Ausgabe: `Verbindung OK, Einträge: 0`

- [ ] **Schritt 7: Commit**

  ```bash
  git add requirements.txt .env.example
  git commit -m "feat: add Supabase dependencies and DB schema"
  ```

---

### Task 2: Domain-Erweiterungen (models.py)

**Files:**
- Modify: `core/domain/models.py`
- Create: `tests/__init__.py`, `tests/test_domain_extensions.py`

- [ ] **Schritt 1: Failing-Test schreiben**

  Erstelle `tests/__init__.py` (leer) und `tests/test_domain_extensions.py`:

  ```python
  from core.domain.models import AnomalyReport, DeepDiveResult, Signal
  from core.domain.recommendation import InvestmentRecommendation, Recommendation


  def test_anomaly_report_no_anomalies():
      report = AnomalyReport(
          has_anomalies=False,
          statistical=[],
          contradictions=[],
          severity="none",
          summary="Keine Anomalien erkannt.",
      )
      assert report.has_anomalies is False
      assert report.severity == "none"


  def test_anomaly_report_high_severity():
      report = AnomalyReport(
          has_anomalies=True,
          statistical=["VIX=45 ist ungewöhnlich hoch (Z=3.2)"],
          contradictions=["Macro=BULLISH widerspricht Sentiment=BEARISH"],
          severity="high",
          summary="Kritische Anomalien erkannt.",
      )
      assert report.severity == "high"
      assert len(report.statistical) == 1
      assert len(report.contradictions) == 1


  def test_deep_dive_result_has_confidence_and_xai():
      rec = InvestmentRecommendation(
          action=Recommendation.BUY,
          short_type=None,
          short_warning=None,
          confidence=0.75,
          reasoning="Test",
      )
      result = DeepDiveResult(
          ticker="AAPL",
          asset_class="equity",
          market="USA",
          top_down_context="Test context",
          top_down_available=True,
          bottom_up=None,
          judgment="Test judgment",
          alignment="aligned_bullish",
          recommendation=rec,
          confidence=0.75,
          xai_explanation="Ausführliche Erklärung...",
      )
      assert result.confidence == 0.75
      assert result.xai_explanation == "Ausführliche Erklärung..."
      assert result.market == "USA"
  ```

- [ ] **Schritt 2: Test ausführen — muss fehlschlagen**

  ```bash
  python -m pytest tests/test_domain_extensions.py -v
  ```

  Erwartete Ausgabe: `FAILED — ImportError: cannot import name 'AnomalyReport'`

- [ ] **Schritt 3: models.py erweitern**

  Am Ende des Abschnitts `# Modus 3 — Kombinations-Urteil` in `core/domain/models.py` folgende Änderungen vornehmen:

  **Neu: AnomalyReport vor InvestmentRecommendation einfügen:**

  ```python
  @dataclass
  class AnomalyReport:
      has_anomalies: bool
      statistical: list[str]
      contradictions: list[str]
      severity: str   # "none" | "low" | "medium" | "high"
      summary: str

      @staticmethod
      def empty() -> "AnomalyReport":
          return AnomalyReport(
              has_anomalies=False,
              statistical=[],
              contradictions=[],
              severity="none",
              summary="Keine Anomalien erkannt.",
          )
  ```

  **DeepDiveResult: vier neue Felder hinzufügen:**

  ```python
  @dataclass
  class DeepDiveResult:
      ticker: str
      asset_class: str
      market: str                    # neu
      top_down_context: str
      top_down_available: bool
      bottom_up: BottomUpResult
      judgment: str
      alignment: str
      recommendation: InvestmentRecommendation
      dominant_signal: str = "neutral"  # neu — "bullish"|"bearish"|"neutral"
      confidence: float = 0.65          # neu
      xai_explanation: str = ""         # neu
  ```

- [ ] **Schritt 4: Test ausführen — muss bestehen**

  ```bash
  python -m pytest tests/test_domain_extensions.py -v
  ```

  Erwartete Ausgabe: `3 passed`

- [ ] **Schritt 5: Commit**

  ```bash
  git add core/domain/models.py tests/
  git commit -m "feat: add AnomalyReport and extend DeepDiveResult"
  ```

---

### Task 3: MemoryPort (Hexagonal-Port)

**Files:**
- Create: `core/ports/memory_port.py`

- [ ] **Schritt 1: memory_port.py erstellen**

  ```python
  from abc import ABC, abstractmethod
  from typing import Optional


  class MemoryPort(ABC):

      @abstractmethod
      def save_analysis(
          self,
          result,           # DeepDiveResult
          cockpit,          # CockpitResult | None
          price: Optional[float],
      ) -> None: ...

      @abstractmethod
      def load_history(self, ticker: str, days: int = 90) -> list[dict]: ...

      @abstractmethod
      def load_global_history(self, days: int = 90) -> list[dict]: ...

      @abstractmethod
      def load_latest_backtester_report(self, backtester_type: str) -> dict: ...

      @abstractmethod
      def save_backtester_report(self, report: dict) -> None: ...

      @abstractmethod
      def save_portfolio_snapshot(self, snapshot: dict) -> None: ...

      @abstractmethod
      def load_latest_portfolio_snapshot(self) -> Optional[dict]: ...
  ```

  Hinweis: Typen als `Any` statt konkrete Imports, um Zirkularimporte zu vermeiden. Die Implementierung prüft die Felder zur Laufzeit.

- [ ] **Schritt 2: Verifikation**

  ```bash
  python -c "from core.ports.memory_port import MemoryPort; print('OK')"
  ```

  Erwartete Ausgabe: `OK`

- [ ] **Schritt 3: Commit**

  ```bash
  git add core/ports/memory_port.py
  git commit -m "feat: add MemoryPort hexagonal interface"
  ```

---

### Task 4: SupabaseMemory Adapter

**Files:**
- Create: `adapters/memory/__init__.py`, `adapters/memory/supabase_memory.py`

- [ ] **Schritt 1: `adapters/memory/__init__.py` erstellen** (leer)

- [ ] **Schritt 2: `adapters/memory/supabase_memory.py` erstellen**

  ```python
  import json
  import os
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
          return psycopg2.connect(self._url, cursor_factory=psycopg2.extras.RealDictCursor)

      # ── Analyse speichern ───────────────────────────────────────────────

      def save_analysis(self, result, cockpit, price: Optional[float] = None) -> None:
          resolved_price = price if price is not None else _extract_price(result)
          indicators = _build_indicators_snapshot(cockpit)
          # bottom-up Indikatoren ergänzen
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
                          "none",   # wird später durch Anomalie-Agent befüllt
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
  ```

- [ ] **Schritt 3: Verifikation (Verbindung + Roundtrip)**

  ```bash
  python -c "
  from dotenv import load_dotenv; load_dotenv()
  from adapters.memory.supabase_memory import SupabaseMemory
  m = SupabaseMemory()
  print('SupabaseMemory OK, History:', m.load_global_history(days=1))
  "
  ```

  Erwartete Ausgabe: `SupabaseMemory OK, History: []`

- [ ] **Schritt 4: Commit**

  ```bash
  git add adapters/memory/
  git commit -m "feat: implement SupabaseMemory adapter"
  ```

---

## PHASE 2 — Analyse-Erweiterungen (Anomalie, Confidence, XAI)

---

### Task 5: Statistik-Hilfsfunktionen

**Files:**
- Create: `core/utils/__init__.py`, `core/utils/statistics.py`
- Create: `tests/test_statistics.py`

- [ ] **Schritt 1: Failing-Test schreiben**

  `tests/test_statistics.py`:

  ```python
  from core.utils.statistics import z_score, compute_severity


  def test_z_score_normal_value():
      history = [10.0, 11.0, 10.5, 10.8, 9.9, 11.2, 10.3]
      assert abs(z_score(10.5, history)) < 1.0


  def test_z_score_outlier():
      history = [10.0, 11.0, 10.5, 10.8, 9.9, 11.2, 10.3]
      assert z_score(25.0, history) > 2.5


  def test_z_score_too_short_history():
      assert z_score(100.0, [10.0, 11.0]) == 0.0


  def test_z_score_zero_std():
      assert z_score(5.0, [5.0, 5.0, 5.0, 5.0, 5.0]) == 0.0


  def test_severity_none():
      assert compute_severity([], []) == "none"


  def test_severity_low_one_statistical():
      assert compute_severity(["VIX anomal"], []) == "low"


  def test_severity_low_one_contradiction():
      assert compute_severity([], ["Macro vs Sentiment"]) == "low"


  def test_severity_medium_two_statistical():
      assert compute_severity(["A", "B"], []) == "medium"


  def test_severity_high_both():
      assert compute_severity(["A"], ["B"]) == "high"
  ```

- [ ] **Schritt 2: Test ausführen — muss fehlschlagen**

  ```bash
  python -m pytest tests/test_statistics.py -v
  ```

  Erwartete Ausgabe: `FAILED — ModuleNotFoundError: No module named 'core.utils'`

- [ ] **Schritt 3: Implementierung**

  `core/utils/__init__.py` — leer.

  `core/utils/statistics.py`:

  ```python
  import math


  Z_THRESHOLD = 2.5


  def z_score(current: float, history: list[float]) -> float:
      if len(history) < 3:
          return 0.0
      mean = sum(history) / len(history)
      variance = sum((v - mean) ** 2 for v in history) / len(history)
      std = math.sqrt(variance) if variance > 0 else 0.0
      if std == 0.0:
          return 0.0
      return (current - mean) / std


  def compute_severity(statistical: list[str], contradictions: list[str]) -> str:
      has_stat = len(statistical) > 0
      has_contra = len(contradictions) > 0
      if has_stat and has_contra:
          return "high"
      if len(statistical) >= 2 or len(contradictions) >= 2:
          return "medium"
      if has_stat or has_contra:
          return "low"
      return "none"
  ```

- [ ] **Schritt 4: Test ausführen — muss bestehen**

  ```bash
  python -m pytest tests/test_statistics.py -v
  ```

  Erwartete Ausgabe: `9 passed`

- [ ] **Schritt 5: Commit**

  ```bash
  git add core/utils/ tests/test_statistics.py
  git commit -m "feat: add statistics utilities (z_score, compute_severity)"
  ```

---

### Task 6: TopDownAnomalyAgent

**Files:**
- Create: `agents/anomaly/__init__.py`, `agents/anomaly/top_down_anomaly_agent.py`
- Create: `tests/test_anomaly_agents.py`

- [ ] **Schritt 1: Failing-Test schreiben**

  `tests/test_anomaly_agents.py`:

  ```python
  from unittest.mock import MagicMock
  from agents.anomaly.top_down_anomaly_agent import TopDownAnomalyAgent
  from core.domain.models import Signal


  def _make_cockpit(vix=18.0, fear_greed=50.0, spread=1.2,
                    macro_signal=Signal.BULLISH, sentiment_signal=Signal.BULLISH,
                    yield_signal=Signal.BULLISH, commodity_signal=Signal.BULLISH,
                    regime_confidence=0.75):
      cockpit = MagicMock()
      cockpit.sentiment.vix.vix = vix
      cockpit.sentiment.vix.signal = sentiment_signal
      cockpit.sentiment.fear_greed.value = fear_greed
      cockpit.sentiment.fear_greed.signal = sentiment_signal
      cockpit.sentiment.put_call.signal = sentiment_signal
      cockpit.yield_curve.yield_spreads.usa.spread_10y2y = spread
      cockpit.yield_curve.yield_spreads.usa.signal = yield_signal
      cockpit.macro.regime_confidence = regime_confidence
      cockpit.macro.inflation.usa.cpi = 3.2
      cockpit.macro.inflation.usa.signal = macro_signal
      cockpit.macro.gdp.usa.signal = macro_signal
      cockpit.commodities.energy.signal = commodity_signal
      cockpit.commodities.industrial_metals.signal = commodity_signal
      cockpit.sectors.rotation.signal = Signal.NEUTRAL
      return cockpit


  def test_no_anomalies_normal_conditions():
      agent = TopDownAnomalyAgent()
      history = [
          {"indicators_snapshot": {"vix": 18.0, "fear_greed": 52.0,
                                   "yield_spread_10y2y": 1.1, "inflation_cpi_usa": 3.1}}
          for _ in range(10)
      ]
      report = agent.run(_make_cockpit(), history)
      assert report.severity == "none"
      assert report.has_anomalies is False


  def test_statistical_anomaly_high_vix():
      agent = TopDownAnomalyAgent()
      history = [
          {"indicators_snapshot": {"vix": 18.0, "fear_greed": 50.0,
                                   "yield_spread_10y2y": 1.0, "inflation_cpi_usa": 3.0}}
          for _ in range(10)
      ]
      report = agent.run(_make_cockpit(vix=45.0), history)
      assert report.has_anomalies is True
      assert any("VIX" in s for s in report.statistical)


  def test_contradiction_macro_vs_sentiment():
      agent = TopDownAnomalyAgent()
      cockpit = _make_cockpit(
          macro_signal=Signal.BULLISH,
          sentiment_signal=Signal.BEARISH,
          yield_signal=Signal.BEARISH,
      )
      report = agent.run(cockpit, [])
      assert report.has_anomalies is True
      assert len(report.contradictions) >= 1


  def test_high_severity_both_types():
      agent = TopDownAnomalyAgent()
      history = [
          {"indicators_snapshot": {"vix": 18.0, "fear_greed": 50.0,
                                   "yield_spread_10y2y": 1.0, "inflation_cpi_usa": 3.0}}
          for _ in range(10)
      ]
      cockpit = _make_cockpit(
          vix=50.0,
          macro_signal=Signal.BULLISH,
          sentiment_signal=Signal.BEARISH,
          yield_signal=Signal.BEARISH,
      )
      report = agent.run(cockpit, history)
      assert report.severity == "high"
  ```

- [ ] **Schritt 2: Test ausführen — muss fehlschlagen**

  ```bash
  python -m pytest tests/test_anomaly_agents.py::test_no_anomalies_normal_conditions -v
  ```

  Erwartete Ausgabe: `FAILED — ModuleNotFoundError`

- [ ] **Schritt 3: `agents/anomaly/__init__.py` erstellen** (leer)

- [ ] **Schritt 4: `agents/anomaly/top_down_anomaly_agent.py` erstellen**

  ```python
  from core.domain.models import AnomalyReport, Signal
  from core.utils.statistics import Z_THRESHOLD, compute_severity, z_score

  _SIGNAL_PAIRS = [
      ("Macro", "Sentiment"),
      ("Macro", "YieldCurve"),
      ("Commodity", "Macro"),
  ]


  def _dominant_sentiment(cockpit) -> Signal:
      signals = [
          cockpit.sentiment.vix.signal,
          cockpit.sentiment.fear_greed.signal,
          cockpit.sentiment.put_call.signal,
      ]
      bullish = signals.count(Signal.BULLISH)
      bearish = signals.count(Signal.BEARISH)
      if bullish > bearish:
          return Signal.BULLISH
      if bearish > bullish:
          return Signal.BEARISH
      return Signal.NEUTRAL


  def _dominant_macro(cockpit) -> Signal:
      signals = [
          cockpit.macro.inflation.usa.signal,
          cockpit.macro.gdp.usa.signal,
      ]
      bullish = signals.count(Signal.BULLISH)
      bearish = signals.count(Signal.BEARISH)
      if bullish > bearish:
          return Signal.BULLISH
      if bearish > bullish:
          return Signal.BEARISH
      return Signal.NEUTRAL


  def _dominant_commodity(cockpit) -> Signal:
      signals = [
          cockpit.commodities.energy.signal,
          cockpit.commodities.industrial_metals.signal,
      ]
      bullish = signals.count(Signal.BULLISH)
      bearish = signals.count(Signal.BEARISH)
      if bullish > bearish:
          return Signal.BULLISH
      if bearish > bullish:
          return Signal.BEARISH
      return Signal.NEUTRAL


  def _contradicts(a: Signal, b: Signal) -> bool:
      return (a == Signal.BULLISH and b == Signal.BEARISH) or \
             (a == Signal.BEARISH and b == Signal.BULLISH)


  class TopDownAnomalyAgent:

      def run(self, cockpit, history: list[dict]) -> AnomalyReport:
          statistical: list[str] = []
          contradictions: list[str] = []

          snapshots = [
              h.get("indicators_snapshot") or {}
              for h in history
              if h.get("indicators_snapshot")
          ]

          # ── Z-Score Checks ──────────────────────────────────────────
          def _check(label: str, current, key: str, direction_label: str = ""):
              if current is None or len(snapshots) < 5:
                  return
              vals = [s[key] for s in snapshots if key in s and s[key] is not None]
              if len(vals) < 5:
                  return
              z = z_score(float(current), [float(v) for v in vals])
              if abs(z) > Z_THRESHOLD:
                  dir_ = "hoch" if z > 0 else "niedrig"
                  statistical.append(
                      f"{label}={current:.1f} ist ungewöhnlich {dir_} (Z={z:.1f})"
                  )

          _check("VIX", cockpit.sentiment.vix.vix, "vix")
          _check("Fear&Greed", cockpit.sentiment.fear_greed.value, "fear_greed")
          yld = cockpit.yield_curve.yield_spreads.usa.spread_10y2y
          _check("Yield-Spread 10J-2J", yld, "yield_spread_10y2y")
          _check("Inflation CPI", cockpit.macro.inflation.usa.cpi, "inflation_cpi_usa")

          rc = cockpit.macro.regime_confidence
          if rc is not None and rc < 0.30:
              statistical.append(
                  f"Regime-Konfidenz={rc:.0%} — Wirtschaftslage schwer einzuordnen"
              )

          # ── Widerspruchs-Checks ─────────────────────────────────────
          macro_sig     = _dominant_macro(cockpit)
          sentiment_sig = _dominant_sentiment(cockpit)
          yield_sig     = cockpit.yield_curve.yield_spreads.usa.signal
          commodity_sig = _dominant_commodity(cockpit)

          area_signals = {
              "Macro":      macro_sig,
              "Sentiment":  sentiment_sig,
              "YieldCurve": yield_sig,
              "Commodity":  commodity_sig,
          }

          pairs = [
              ("Macro", "Sentiment"),
              ("Macro", "YieldCurve"),
              ("Commodity", "Macro"),
          ]
          for a, b in pairs:
              if _contradicts(area_signals[a], area_signals[b]):
                  contradictions.append(
                      f"{a}={area_signals[a].value} widerspricht {b}={area_signals[b].value}"
                  )

          severity = compute_severity(statistical, contradictions)
          summary  = _build_summary(statistical, contradictions, severity)

          return AnomalyReport(
              has_anomalies=bool(statistical or contradictions),
              statistical=statistical,
              contradictions=contradictions,
              severity=severity,
              summary=summary,
          )


  def _build_summary(statistical: list[str], contradictions: list[str], severity: str) -> str:
      if severity == "none":
          return "Keine Top-Down-Anomalien erkannt."
      lines = [f"Top-Down Anomalie-Bericht (Schwere: {severity.upper()}):"]
      for s in statistical:
          lines.append(f"  [STATISTISCH] {s}")
      for c in contradictions:
          lines.append(f"  [WIDERSPRUCH] {c}")
      return "\n".join(lines)
  ```

- [ ] **Schritt 5: Tests ausführen**

  ```bash
  python -m pytest tests/test_anomaly_agents.py -k "TopDown or top_down or no_anomalies or statistical or contradiction or high_severity" -v
  ```

  Erwartete Ausgabe: `4 passed`

- [ ] **Schritt 6: Commit**

  ```bash
  git add agents/anomaly/ tests/test_anomaly_agents.py
  git commit -m "feat: add TopDownAnomalyAgent"
  ```

---

### Task 7: BottomUpAnomalyAgent

**Files:**
- Modify: `agents/anomaly/bottom_up_anomaly_agent.py` (neu)
- Modify: `tests/test_anomaly_agents.py` (Tests ergänzen)

- [ ] **Schritt 1: Failing-Tests ergänzen in `tests/test_anomaly_agents.py`**

  Am Ende der Datei hinzufügen:

  ```python
  from agents.anomaly.bottom_up_anomaly_agent import BottomUpAnomalyAgent


  def _make_bottom_up(pe=22.0, short_float=3.0, insider_tx=2,
                      fund_signal=Signal.BULLISH, val_signal=Signal.BULLISH,
                      earn_signal=Signal.BULLISH, quality_signal=Signal.BULLISH,
                      asset_class="equity"):
      bu = MagicMock()
      bu.asset_class = asset_class
      bu.fundamentals.pe_ratio = pe
      bu.fundamentals.signal = fund_signal
      bu.short_interest.short_float_pct = short_float
      bu.short_interest.signal = Signal.NEUTRAL
      bu.insider.recent_transactions = insider_tx
      bu.insider.signal = Signal.NEUTRAL
      bu.earnings_trend.signal = earn_signal
      bu.moat.signal = Signal.NEUTRAL
      bu.valuation_range.signal = val_signal
      bu.quality.signal = quality_signal
      return bu


  def test_bottomup_no_anomalies():
      agent = BottomUpAnomalyAgent()
      history = [
          {"indicators_snapshot": {"pe_ratio": 22.0, "short_float_pct": 3.0}}
          for _ in range(10)
      ]
      report = agent.run(_make_bottom_up(), history)
      assert report.severity == "none"


  def test_bottomup_pe_statistical_anomaly():
      agent = BottomUpAnomalyAgent()
      history = [
          {"indicators_snapshot": {"pe_ratio": 22.0, "short_float_pct": 3.0}}
          for _ in range(10)
      ]
      report = agent.run(_make_bottom_up(pe=85.0), history)
      assert report.has_anomalies is True
      assert any("KGV" in s for s in report.statistical)


  def test_bottomup_contradiction():
      agent = BottomUpAnomalyAgent()
      report = agent.run(
          _make_bottom_up(fund_signal=Signal.BULLISH, val_signal=Signal.BEARISH,
                          earn_signal=Signal.BEARISH, quality_signal=Signal.BEARISH),
          []
      )
      assert report.has_anomalies is True
      assert len(report.contradictions) >= 1


  def test_bottomup_non_equity_skips_z_score():
      agent = BottomUpAnomalyAgent()
      bu = MagicMock()
      bu.asset_class = "bond"
      bu.fundamentals = None
      bu.short_interest = None
      bu.insider = None
      bu.earnings_trend = MagicMock()
      bu.earnings_trend.signal = Signal.NEUTRAL
      bu.moat = MagicMock()
      bu.moat.signal = Signal.NEUTRAL
      bu.valuation_range = MagicMock()
      bu.valuation_range.signal = Signal.NEUTRAL
      bu.quality = MagicMock()
      bu.quality.signal = Signal.NEUTRAL
      history = [{"indicators_snapshot": {"pe_ratio": 22.0}} for _ in range(10)]
      report = agent.run(bu, history)
      assert report.severity == "none"
  ```

- [ ] **Schritt 2: Test ausführen — muss fehlschlagen**

  ```bash
  python -m pytest tests/test_anomaly_agents.py::test_bottomup_no_anomalies -v
  ```

  Erwartete Ausgabe: `FAILED — ImportError`

- [ ] **Schritt 3: `agents/anomaly/bottom_up_anomaly_agent.py` erstellen**

  ```python
  from core.domain.models import AnomalyReport, Signal
  from core.utils.statistics import Z_THRESHOLD, compute_severity, z_score


  def _contradicts(a: Signal, b: Signal) -> bool:
      return (a == Signal.BULLISH and b == Signal.BEARISH) or \
             (a == Signal.BEARISH and b == Signal.BULLISH)


  class BottomUpAnomalyAgent:

      def run(self, bottom_up, history: list[dict]) -> AnomalyReport:
          statistical: list[str] = []
          contradictions: list[str] = []

          is_equity = bottom_up.asset_class in ("equity", "etf")
          snapshots = [
              h.get("indicators_snapshot") or {}
              for h in history
              if h.get("indicators_snapshot")
          ]
          enough_history = len(snapshots) >= 5

          # ── Z-Score Checks (nur Equity, nur bei genug History) ──────
          if is_equity and enough_history:
              def _check(label: str, current, key: str):
                  if current is None:
                      return
                  vals = [s[key] for s in snapshots if key in s and s[key] is not None]
                  if len(vals) < 5:
                      return
                  z = z_score(float(current), [float(v) for v in vals])
                  if abs(z) > Z_THRESHOLD:
                      dir_ = "hoch" if z > 0 else "niedrig"
                      statistical.append(
                          f"{label}={current:.1f} ist ungewöhnlich {dir_} (Z={z:.1f})"
                      )

              fu = bottom_up.fundamentals
              si = bottom_up.short_interest
              ins = bottom_up.insider

              if fu:
                  _check("KGV", fu.pe_ratio, "pe_ratio")
              if si:
                  _check("Short-Float", si.short_float_pct, "short_float_pct")
              if ins and ins.recent_transactions is not None and ins.recent_transactions > 10:
                  statistical.append(
                      f"Ungewöhnlich hohe Insider-Aktivität: {ins.recent_transactions} Transaktionen"
                  )

          # ── Widerspruchs-Checks (alle Asset-Klassen) ────────────────
          if is_equity:
              signals = {
                  "Fundamentals": bottom_up.fundamentals.signal if bottom_up.fundamentals else Signal.NEUTRAL,
                  "Valuation":    bottom_up.valuation_range.signal if bottom_up.valuation_range else Signal.NEUTRAL,
                  "Earnings":     bottom_up.earnings_trend.signal if bottom_up.earnings_trend else Signal.NEUTRAL,
                  "Quality":      bottom_up.quality.signal if bottom_up.quality else Signal.NEUTRAL,
                  "ShortInterest": bottom_up.short_interest.signal if bottom_up.short_interest else Signal.NEUTRAL,
                  "Moat":         bottom_up.moat.signal if bottom_up.moat else Signal.NEUTRAL,
              }
              bullish_count = sum(1 for s in signals.values() if s == Signal.BULLISH)
              bearish_count = sum(1 for s in signals.values() if s == Signal.BEARISH)

              if bullish_count > 0 and bearish_count > 0:
                  conflicting = [name for name, s in signals.items() if s == Signal.BEARISH]
                  if _contradicts(signals["Fundamentals"], signals["Valuation"]):
                      contradictions.append(
                          "Fundamentals=BULLISH widerspricht Valuation=BEARISH"
                          if signals["Fundamentals"] == Signal.BULLISH
                          else "Valuation=BULLISH widerspricht Fundamentals=BEARISH"
                      )
                  if _contradicts(signals["Earnings"], signals["Quality"]):
                      contradictions.append(
                          "Earnings widerspricht Quality-Signal"
                      )
                  if bearish_count >= 3:
                      contradictions.append(
                          f"Mehrheit der Bottom-Up-Signale bearish: {', '.join(conflicting)}"
                      )

          severity = compute_severity(statistical, contradictions)
          summary  = _build_summary(statistical, contradictions, severity)

          return AnomalyReport(
              has_anomalies=bool(statistical or contradictions),
              statistical=statistical,
              contradictions=contradictions,
              severity=severity,
              summary=summary,
          )


  def _build_summary(statistical: list[str], contradictions: list[str], severity: str) -> str:
      if severity == "none":
          return "Keine Bottom-Up-Anomalien erkannt."
      lines = [f"Bottom-Up Anomalie-Bericht (Schwere: {severity.upper()}):"]
      for s in statistical:
          lines.append(f"  [STATISTISCH] {s}")
      for c in contradictions:
          lines.append(f"  [WIDERSPRUCH] {c}")
      return "\n".join(lines)
  ```

- [ ] **Schritt 4: Alle Anomalie-Tests ausführen**

  ```bash
  python -m pytest tests/test_anomaly_agents.py -v
  ```

  Erwartete Ausgabe: `8 passed`

- [ ] **Schritt 5: Commit**

  ```bash
  git add agents/anomaly/bottom_up_anomaly_agent.py tests/test_anomaly_agents.py
  git commit -m "feat: add BottomUpAnomalyAgent"
  ```

---

### Task 8: recommendation.py Refactor + Confidence-Berechnung

**Files:**
- Modify: `core/domain/recommendation.py`
- Create: `tests/test_confidence.py`

- [ ] **Schritt 1: Failing-Tests schreiben**

  `tests/test_confidence.py`:

  ```python
  from core.domain.models import AnomalyReport, Signal
  from core.domain.recommendation import compute_confidence, derive_recommendation, Recommendation


  def _empty_anomaly():
      return AnomalyReport(False, [], [], "none", "")


  def _anomaly(severity: str):
      return AnomalyReport(True, ["x"], [], severity, "")


  def test_confidence_baseline_aligned_bullish():
      conf = compute_confidence(
          alignment="aligned_bullish",
          regime_confidence=0.75,
          td_anomaly=_empty_anomaly(),
          bu_anomaly=_empty_anomaly(),
      )
      assert conf == round(0.70 + 0.10, 2)


  def test_confidence_deduction_contradicting():
      conf = compute_confidence(
          alignment="contradicting",
          regime_confidence=0.75,
          td_anomaly=_empty_anomaly(),
          bu_anomaly=_empty_anomaly(),
      )
      assert conf == round(0.70 - 0.15, 2)


  def test_confidence_high_anomaly_deduction():
      conf = compute_confidence(
          alignment="mixed",
          regime_confidence=0.75,
          td_anomaly=_anomaly("high"),
          bu_anomaly=_anomaly("high"),
      )
      assert conf <= 0.20


  def test_confidence_floor():
      conf = compute_confidence(
          alignment="contradicting",
          regime_confidence=0.20,
          td_anomaly=_anomaly("high"),
          bu_anomaly=_anomaly("high"),
      )
      assert conf == 0.10


  def test_cash_bias_below_0_50():
      rec = derive_recommendation(
          alignment="mixed",
          signal=Signal.BULLISH,
          asset_class="equity",
          in_portfolio=False,
          market="USA",
          cockpit=None,
          top_down_available=False,
          confidence=0.45,
      )
      assert rec.action == Recommendation.HOLD
      assert "widersprüchlich" in rec.reasoning


  def test_cash_bias_below_0_35():
      rec = derive_recommendation(
          alignment="mixed",
          signal=Signal.BULLISH,
          asset_class="equity",
          in_portfolio=False,
          market="USA",
          cockpit=None,
          top_down_available=False,
          confidence=0.30,
      )
      assert rec.action == Recommendation.HOLD
      assert "Cash" in rec.reasoning


  def test_normal_buy_high_confidence():
      rec = derive_recommendation(
          alignment="aligned_bullish",
          signal=Signal.BULLISH,
          asset_class="equity",
          in_portfolio=False,
          market="USA",
          cockpit=None,
          top_down_available=False,
          confidence=0.80,
      )
      assert rec.action == Recommendation.BUY
  ```

- [ ] **Schritt 2: Test ausführen — muss fehlschlagen**

  ```bash
  python -m pytest tests/test_confidence.py -v
  ```

  Erwartete Ausgabe: `FAILED — ImportError: cannot import name 'compute_confidence'`

- [ ] **Schritt 3: `core/domain/recommendation.py` vollständig ersetzen**

  ```python
  from core.domain.models import (
      AnomalyReport, CockpitResult,
      InvestmentRecommendation, Recommendation, ShortType, Signal,
  )
  from typing import Optional

  FULL_ANALYSIS_MARKETS = {"USA", "EU", "CH"}

  SHORT_WARNINGS = {
      ShortType.DEFENSIVE: (
          "⚠️ SHORTPOSITION — DEFENSIV\n"
          "Hierbei handelt es sich um eine Short-Position zur Absicherung "
          "des Portfolios gegen fallende Kurse von ETFs oder Indizes."
      ),
      ShortType.AGGRESSIVE: (
          "⚠️ SHORTPOSITION — AGGRESSIV\n"
          "Hierbei handelt es sich um eine spekulative Short-Position mit der "
          "Absicht, von fallenden Kursen eines Einzelwerts zu profitieren "
          "(Einzelaktien, Edelmetalle, Rohstoffe, Anleihen)."
      ),
  }

  ETF_ASSET_CLASSES      = {"etf", "index"}
  AGGRESSIVE_ASSET_CLASSES = {"equity", "precious_metal", "commodity", "bond"}


  def _short_type(asset_class: str) -> ShortType:
      if asset_class.lower() in ETF_ASSET_CLASSES:
          return ShortType.DEFENSIVE
      return ShortType.AGGRESSIVE


  _SEVERITY_DEDUCTION = {"none": 0.0, "low": -0.05, "medium": -0.15, "high": -0.25}


  def compute_confidence(
      alignment: str,
      regime_confidence: float,
      td_anomaly: AnomalyReport,
      bu_anomaly: AnomalyReport,
  ) -> float:
      score = 0.70

      if alignment == "aligned_bullish" or alignment == "aligned_bearish":
          score += 0.10
      elif alignment == "contradicting":
          score -= 0.15
      elif alignment == "mixed":
          score -= 0.05

      score += _SEVERITY_DEDUCTION.get(td_anomaly.severity, 0.0)
      score += _SEVERITY_DEDUCTION.get(bu_anomaly.severity, 0.0)

      if regime_confidence < 0.4:
          score -= 0.10

      return round(max(0.10, min(1.0, score)), 2)


  def derive_recommendation(
      alignment: str,
      signal: Signal,
      asset_class: str,
      in_portfolio: bool,
      market: str,
      cockpit: Optional[CockpitResult],
      top_down_available: bool,
      confidence: float,
  ) -> InvestmentRecommendation:

      # Cash-Bias bei niedriger Konfidenz
      if confidence < 0.35:
          return InvestmentRecommendation(
              action=Recommendation.HOLD,
              short_type=None,
              short_warning=None,
              confidence=confidence,
              reasoning=(
                  "Stark widersprüchliche oder anomale Signale — Cash bevorzugen, "
                  "kein neues Kapital einsetzen."
              ),
          )
      if confidence < 0.50:
          return InvestmentRecommendation(
              action=Recommendation.HOLD,
              short_type=None,
              short_warning=None,
              confidence=confidence,
              reasoning="Signallage zu widersprüchlich — Abwarten empfohlen.",
          )

      full_analysis = top_down_available and market in FULL_ANALYSIS_MARKETS
      bearish = signal == Signal.BEARISH or alignment in ("aligned_bearish", "contradicting")
      bullish = signal == Signal.BULLISH or alignment == "aligned_bullish"

      if bearish and not in_portfolio and full_analysis:
          short_t = _short_type(asset_class)
          return InvestmentRecommendation(
              action=Recommendation.SHORT,
              short_type=short_t,
              short_warning=SHORT_WARNINGS[short_t],
              confidence=confidence,
              reasoning="Bearish Signal ohne bestehende Portfolio-Position — Short möglich.",
          )

      if bearish and in_portfolio:
          return InvestmentRecommendation(
              action=Recommendation.SELL,
              short_type=None,
              short_warning=None,
              confidence=confidence,
              reasoning="Bearish Signal bei bestehender Portfolio-Position — Verkauf empfohlen.",
          )

      if bullish and not in_portfolio:
          return InvestmentRecommendation(
              action=Recommendation.BUY,
              short_type=None,
              short_warning=None,
              confidence=confidence,
              reasoning="Bullish Signal ohne bestehende Portfolio-Position — Kauf empfohlen.",
          )

      return InvestmentRecommendation(
          action=Recommendation.HOLD,
          short_type=None,
          short_warning=None,
          confidence=confidence,
          reasoning="Kein klares Kauf- oder Verkaufssignal — Position halten.",
      )
  ```

- [ ] **Schritt 4: Tests ausführen**

  ```bash
  python -m pytest tests/test_confidence.py -v
  ```

  Erwartete Ausgabe: `7 passed`

- [ ] **Schritt 5: Commit**

  ```bash
  git add core/domain/recommendation.py tests/test_confidence.py
  git commit -m "feat: add compute_confidence and cash-bias to derive_recommendation"
  ```

---

### Task 9: JudgmentAgent erweitern (Confidence + XAI)

**Files:**
- Modify: `agents/judgment/judgment_agent.py`

- [ ] **Schritt 1: Vollständige neue Version von `agents/judgment/judgment_agent.py`**

  ```python
  import asyncio

  from core.domain.events import DeepDiveResultReady
  from core.domain.models import (
      AnomalyReport, BottomUpResult, CockpitResult, DeepDiveResult, Signal,
  )
  from core.domain.recommendation import compute_confidence, derive_recommendation
  from core.ports.event_bus import EventBus
  from core.ports.llm_provider import LLMProvider

  SYSTEM_PROMPT = """Du bist ein erfahrener Aktienanalyst.
  Du kombinierst makroökonomischen Top-Down-Kontext mit Bottom-Up-Fundamentalanalyse.
  Deine Urteile sind präzise, direkt und faktenbasiert. Maximal 4 Sätze."""

  XAI_SYSTEM_PROMPT = """Du bist ein erfahrener Finanzanalyst und erklärst Anlageentscheidungen.
  Schreibe eine ausführliche, nachvollziehbare Begründung für die getroffene Empfehlung.
  Struktur (alle 5 Punkte ausführen):
  (1) Top-Down-Analyse: welche makroökonomischen Signale waren entscheidend und warum
  (2) Bottom-Up-Analyse: welche Kennzahlen haben die Entscheidung beeinflusst
  (3) Widersprüche: wo lagen sie und wie wurden sie aufgelöst
  (4) Konfidenz: warum diese Stufe — was macht die Lage unsicher oder klar
  (5) Kipppunkte: welche Entwicklungen würden die Einschätzung ändern
  Kein Fachjargon. Direkt, klar und für einen informierten Anleger verständlich."""


  def _derive_alignment(signals: list[Signal]) -> str:
      valid   = [s for s in signals if s is not None]
      bullish = valid.count(Signal.BULLISH)
      bearish = valid.count(Signal.BEARISH)
      if bullish >= 3 and bearish == 0:
          return "aligned_bullish"
      if bearish >= 3 and bullish == 0:
          return "aligned_bearish"
      if bullish > 0 and bearish > 0:
          return "contradicting"
      return "mixed"


  def _dominant_signal(signals: list[Signal]) -> Signal:
      valid   = [s for s in signals if s is not None]
      if not valid:
          return Signal.NEUTRAL
      bullish = valid.count(Signal.BULLISH)
      bearish = valid.count(Signal.BEARISH)
      if bullish > bearish:
          return Signal.BULLISH
      if bearish > bullish:
          return Signal.BEARISH
      return Signal.NEUTRAL


  def _backtester_summary(context: dict) -> str:
      if not context:
          return "Noch kein Backtesting-Report verfügbar (System läuft erst seit Kurzem)."
      acc = context.get("accuracy_30d")
      if acc is not None:
          return f"System-Treffsicherheit (30 Tage): {acc:.0%}"
      notes = context.get("notes", "")
      return notes or "Backtesting-Daten vorhanden."


  class JudgmentAgent:
      def __init__(self, llm: LLMProvider, bus: EventBus):
          self.llm = llm
          self.bus = bus

      async def run(
          self,
          ticker: str,
          top_down_context: str,
          bottom_up: BottomUpResult,
          cockpit: CockpitResult,
          market: str,
          in_portfolio: bool,
          top_down_available: bool,
          top_down_anomaly: AnomalyReport,
          bottom_up_anomaly: AnomalyReport,
          backtester_context: dict,
      ) -> DeepDiveResult:
          fu  = bottom_up.fundamentals
          si  = bottom_up.short_interest
          ins = bottom_up.insider
          et  = bottom_up.earnings_trend
          mo  = bottom_up.moat
          vr  = bottom_up.valuation_range

          all_signals = [
              fu.signal  if fu  else None,
              si.signal  if si  else None,
              ins.signal if ins else None,
              et.signal  if et  else None,
              mo.signal  if mo  else None,
              vr.signal  if vr  else None,
          ]
          alignment       = _derive_alignment(all_signals)
          dominant_signal = _dominant_signal(all_signals)

          fu_line  = f"- Fundamentals: KGV={fu.pe_ratio}, Marge={fu.operating_margin}% → {fu.signal.value}" if fu  else "- Fundamentals: n/v"
          si_line  = f"- Short Interest: {si.short_float_pct}%, DTC={si.days_to_cover} → {si.signal.value}" if si  else "- Short Interest: n/v"
          ins_line = f"- Insider: {ins.net_direction} ({ins.recent_transactions} Tx) → {ins.signal.value}" if ins else "- Insider: n/v"
          et_line  = f"- Earnings: Beat={et.beat_rate}, Revision={et.estimate_revision} → {et.signal.value}" if et  else "- Earnings: n/v"
          mo_line  = f"- Burggraben: {mo.overall} (Score {mo.total_score}/10) → {mo.signal.value}" if mo  else "- Burggraben: n/v"
          vr_line  = f"- Bewertung: {vr.position} [{vr.combined_low:.0f}–{vr.combined_high:.0f}] → {vr.signal.value}" if vr  else "- Bewertung: n/v"

          prompt = f"""Aktie: {ticker} | Markt: {market} | Asset-Klasse: {bottom_up.asset_class}

  TOP-DOWN KONTEXT:
  {top_down_context}

  BOTTOM-UP SIGNALE:
  {fu_line}
  {si_line}
  {ins_line}
  {et_line}
  {mo_line}
  {vr_line}

  ALIGNMENT: {alignment}

  TOP-DOWN ANOMALIEN:
  {top_down_anomaly.summary}

  BOTTOM-UP ANOMALIEN:
  {bottom_up_anomaly.summary}

  SYSTEM-TREFFSICHERHEIT:
  {_backtester_summary(backtester_context)}

  Kombiniere Top-Down und Bottom-Up zu einem klaren Urteil. Gibt es Widersprüche?"""

          # LLM-Call 1: Urteil
          judgment = await asyncio.to_thread(self.llm.complete, prompt, SYSTEM_PROMPT)

          # Confidence berechnen
          regime_conf = cockpit.macro.regime_confidence if cockpit else 0.5
          confidence = compute_confidence(
              alignment=alignment,
              regime_confidence=regime_conf,
              td_anomaly=top_down_anomaly,
              bu_anomaly=bottom_up_anomaly,
          )

          # Empfehlung ableiten (mit Confidence + Cash-Bias)
          recommendation = derive_recommendation(
              alignment=alignment,
              signal=dominant_signal,
              asset_class=bottom_up.asset_class,
              in_portfolio=in_portfolio,
              market=market,
              cockpit=cockpit,
              top_down_available=top_down_available,
              confidence=confidence,
          )

          # LLM-Call 2: XAI-Erklärung
          xai_prompt = f"""Aktie: {ticker} | Empfehlung: {recommendation.action.value} | Konfidenz: {confidence:.0%}

  TOP-DOWN KONTEXT:
  {top_down_context}

  BOTTOM-UP SIGNALE:
  {fu_line}
  {si_line}
  {ins_line}
  {et_line}
  {mo_line}
  {vr_line}

  ALIGNMENT: {alignment}

  ANOMALIEN:
  {top_down_anomaly.summary}
  {bottom_up_anomaly.summary}

  URTEIL DES ANALYSTEN:
  {judgment}

  Erkläre ausführlich warum diese Empfehlung getroffen wurde."""

          xai_explanation = await asyncio.to_thread(
              self.llm.complete, xai_prompt, XAI_SYSTEM_PROMPT
          )

          result = DeepDiveResult(
              ticker=ticker,
              asset_class=bottom_up.asset_class,
              market=market,
              top_down_context=top_down_context,
              top_down_available=top_down_available,
              bottom_up=bottom_up,
              judgment=judgment,
              alignment=alignment,
              recommendation=recommendation,
              dominant_signal=dominant_signal.value,
              confidence=confidence,
              xai_explanation=xai_explanation,
          )

          self.bus.publish(DeepDiveResultReady(source="judgment_agent", payload={
              "ticker": ticker,
              "alignment": alignment,
              "recommendation": recommendation.action.value,
              "confidence": confidence,
          }))

          return result
  ```

- [ ] **Schritt 2: Verifikation (Import-Check)**

  ```bash
  python -c "from agents.judgment.judgment_agent import JudgmentAgent; print('OK')"
  ```

  Erwartete Ausgabe: `OK`

- [ ] **Schritt 3: Commit**

  ```bash
  git add agents/judgment/judgment_agent.py
  git commit -m "feat: extend JudgmentAgent with confidence, XAI, and anomaly context"
  ```

---

### Task 10: JudgmentOrchestrator erweitern

**Files:**
- Modify: `orchestrators/judgment_orchestrator.py`

- [ ] **Schritt 1: `orchestrators/judgment_orchestrator.py` vollständig ersetzen**

  ```python
  from agents.anomaly.bottom_up_anomaly_agent import BottomUpAnomalyAgent
  from agents.anomaly.top_down_anomaly_agent import TopDownAnomalyAgent
  from agents.judgment.judgment_agent import JudgmentAgent
  from core.domain.models import AnomalyReport, BottomUpResult, CockpitResult, DeepDiveResult
  from core.domain.top_down_context import derive_top_down_context
  from core.ports.event_bus import EventBus
  from core.ports.llm_provider import LLMProvider
  from core.ports.memory_port import MemoryPort

  FULL_ANALYSIS_MARKETS = {"USA", "EU", "CH"}


  class JudgmentOrchestrator:
      """
      Modus 3 — Kombinations-Urteil.
      Führt Anomalie-Erkennung durch, lädt Backtester-Kontext,
      ruft JudgmentAgent auf und speichert Ergebnis im Memory.
      """

      def __init__(self, llm: LLMProvider, bus: EventBus, memory: MemoryPort):
          self.judgment_agent      = JudgmentAgent(llm, bus)
          self.td_anomaly_agent    = TopDownAnomalyAgent()
          self.bu_anomaly_agent    = BottomUpAnomalyAgent()
          self.memory              = memory

      async def run(
          self,
          cockpit: CockpitResult,
          bottom_up: BottomUpResult,
          market: str,
          in_portfolio: bool = False,
          sector: str = "default",
      ) -> DeepDiveResult:
          top_down_available = cockpit is not None and market in FULL_ANALYSIS_MARKETS
          top_down_context   = (
              derive_top_down_context(cockpit, sector=sector)
              if top_down_available
              else f"Kein vollständiger Top-Down-Kontext verfügbar (Markt: {market})."
          )

          # History aus Memory für Anomalie-Agenten
          ticker_history = self.memory.load_history(bottom_up.ticker, days=90)
          global_history = self.memory.load_global_history(days=90)

          # Anomalie-Erkennung
          td_anomaly = (
              self.td_anomaly_agent.run(cockpit, global_history)
              if cockpit is not None
              else AnomalyReport.empty()
          )
          bu_anomaly = self.bu_anomaly_agent.run(bottom_up, ticker_history)

          # Letzten Judgment-Backtester-Report laden
          backtester_context = self.memory.load_latest_backtester_report("judgment")

          # Urteil generieren
          result = await self.judgment_agent.run(
              ticker=bottom_up.ticker,
              top_down_context=top_down_context,
              bottom_up=bottom_up,
              cockpit=cockpit,
              market=market,
              in_portfolio=in_portfolio,
              top_down_available=top_down_available,
              top_down_anomaly=td_anomaly,
              bottom_up_anomaly=bu_anomaly,
              backtester_context=backtester_context,
          )

          # Ergebnis in Memory speichern
          self.memory.save_analysis(result, cockpit, price=None)

          return result
  ```

- [ ] **Schritt 2: Verifikation**

  ```bash
  python -c "from orchestrators.judgment_orchestrator import JudgmentOrchestrator; print('OK')"
  ```

  Erwartete Ausgabe: `OK`

- [ ] **Schritt 3: Commit**

  ```bash
  git add orchestrators/judgment_orchestrator.py
  git commit -m "feat: extend JudgmentOrchestrator with anomaly detection and memory"
  ```

---

## PHASE 3 — Hintergrundsystem (Portfolio, Backtester, Runner)

---

### Task 11: PortfolioMonitorAgent

**Files:**
- Create: `agents/portfolio/__init__.py`, `agents/portfolio/portfolio_monitor_agent.py`
- Create: `data/portfolio.json`
- Create: `tests/test_portfolio_monitor.py`

- [ ] **Schritt 1: `data/portfolio.json` erstellen**

  ```json
  {
    "positions": []
  }
  ```

- [ ] **Schritt 2: Failing-Tests schreiben**

  `tests/test_portfolio_monitor.py`:

  ```python
  from unittest.mock import MagicMock, patch
  from agents.portfolio.portfolio_monitor_agent import PortfolioMonitorAgent, _check_cluster_risks


  def _make_memory(last_recs: dict = None):
      memory = MagicMock()
      if last_recs:
          def load_history(ticker, days=90):
              if ticker in last_recs:
                  return [{"recommendation": last_recs[ticker]}]
              return []
          memory.load_history.side_effect = load_history
      else:
          memory.load_history.return_value = []
      return memory


  def test_empty_portfolio_skips():
      agent = PortfolioMonitorAgent(_make_memory(), MagicMock())
      result = agent._evaluate_positions([])
      assert result["overall_health"] == "green"
      assert result["total_positions"] == 0
      assert result["alerts"] == []


  def test_sector_cluster_risk():
      positions = [
          {"ticker": "AAPL", "shares": 10, "buy_price": 100, "sector": "Technology",
           "asset_class": "equity", "country": "USA", "current_price": 110},
          {"ticker": "MSFT", "shares": 10, "buy_price": 100, "sector": "Technology",
           "asset_class": "equity", "country": "USA", "current_price": 110},
          {"ticker": "NVDA", "shares": 2,  "buy_price": 100, "sector": "Technology",
           "asset_class": "equity", "country": "USA", "current_price": 110},
      ]
      risks = _check_cluster_risks(positions)
      sector_risk = [r for r in risks if r["type"] == "sector"]
      assert len(sector_risk) == 1
      assert sector_risk[0]["name"] == "Technology"


  def test_loss_alert():
      positions = [
          {"ticker": "AAPL", "shares": 10, "buy_price": 200, "sector": "Technology",
           "asset_class": "equity", "country": "USA", "current_price": 160},
      ]
      agent = PortfolioMonitorAgent(_make_memory(), MagicMock())
      result = agent._evaluate_positions(positions)
      loss_alerts = [a for a in result["alerts"] if "Verlust" in a]
      assert len(loss_alerts) == 1


  def test_health_green_no_alerts():
      positions = [
          {"ticker": "AAPL", "shares": 5, "buy_price": 150, "sector": "Technology",
           "asset_class": "equity", "country": "USA", "current_price": 160},
          {"ticker": "JNJ",  "shares": 5, "buy_price": 150, "sector": "Healthcare",
           "asset_class": "equity", "country": "USA", "current_price": 155},
      ]
      agent = PortfolioMonitorAgent(_make_memory(), MagicMock())
      result = agent._evaluate_positions(positions)
      assert result["overall_health"] == "green"
  ```

- [ ] **Schritt 3: Tests ausführen — muss fehlschlagen**

  ```bash
  python -m pytest tests/test_portfolio_monitor.py -v
  ```

  Erwartete Ausgabe: `FAILED — ImportError`

- [ ] **Schritt 4: `agents/portfolio/__init__.py` erstellen** (leer)

- [ ] **Schritt 5: `agents/portfolio/portfolio_monitor_agent.py` erstellen**

  ```python
  import json
  import os
  from typing import Optional

  import yfinance as yf

  from core.ports.memory_port import MemoryPort

  PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "portfolio.json")

  SECTOR_THRESHOLD      = 0.40   # > 40% in einem Sektor → Warnung
  ASSET_CLASS_THRESHOLD = 0.80   # > 80% in einer Asset-Klasse → Warnung
  COUNTRY_THRESHOLD     = 0.70   # > 70% in einem Land → Warnung
  LOSS_THRESHOLD        = 0.15   # > 15% Verlust → Warnung


  def _fetch_current_price(ticker: str) -> Optional[float]:
      try:
          info = yf.Ticker(ticker).fast_info
          return float(info["last_price"])
      except Exception:
          return None


  def _check_cluster_risks(positions: list[dict]) -> list[dict]:
      if not positions:
          return []

      total_value = sum(p["shares"] * p["current_price"] for p in positions)
      if total_value == 0:
          return []

      risks = []

      for dim, key in [("sector", "sector"), ("asset_class", "asset_class"), ("country", "country")]:
          threshold = {
              "sector": SECTOR_THRESHOLD,
              "asset_class": ASSET_CLASS_THRESHOLD,
              "country": COUNTRY_THRESHOLD,
          }[dim]

          buckets: dict[str, float] = {}
          for p in positions:
              val = p["shares"] * p["current_price"]
              name = p.get(key, "Unbekannt")
              buckets[name] = buckets.get(name, 0.0) + val

          for name, val in buckets.items():
              pct = val / total_value
              if pct > threshold:
                  risks.append({
                      "type": dim,
                      "name": name,
                      "pct": round(pct, 3),
                      "threshold": threshold,
                      "message": f"Klumpenrisiko {dim.title()}: {name} = {pct:.0%} (Grenze: {threshold:.0%})",
                  })

      return risks


  class PortfolioMonitorAgent:

      def __init__(self, memory: MemoryPort, market_provider=None):
          self.memory = memory

      def _evaluate_positions(self, positions: list[dict]) -> dict:
          if not positions:
              return {
                  "total_positions": 0,
                  "total_value_usd": 0.0,
                  "cluster_risks": [],
                  "alerts": [],
                  "overall_health": "green",
              }

          # Aktuelle Preise ergänzen (wenn nicht schon vorhanden)
          for p in positions:
              if "current_price" not in p:
                  price = _fetch_current_price(p["ticker"])
                  p["current_price"] = price if price else p["buy_price"]

          total_value = sum(p["shares"] * p["current_price"] for p in positions)
          cluster_risks = _check_cluster_risks(positions)
          alerts: list[str] = []

          # Klumpenrisiko-Alerts
          for risk in cluster_risks:
              alerts.append(risk["message"])

          # Verlust-Alerts
          for p in positions:
              if p["buy_price"] > 0:
                  loss_pct = (p["current_price"] - p["buy_price"]) / p["buy_price"]
                  if loss_pct < -LOSS_THRESHOLD:
                      alerts.append(
                          f"Offener Verlust {p['ticker']}: {loss_pct:.0%} "
                          f"(Kauf: {p['buy_price']:.2f}, Heute: {p['current_price']:.2f})"
                      )

          # Alignment-Check: letzte Empfehlung war SELL/SHORT?
          for p in positions:
              history = self.memory.load_history(p["ticker"], days=90)
              if history:
                  last_rec = history[0].get("recommendation", "")
                  if last_rec in ("SELL", "SHORT"):
                      alerts.append(
                          f"Alignment-Warnung {p['ticker']}: letzte Analyse = {last_rec}, "
                          f"Position aber noch gehalten."
                      )

          n_alerts = len(alerts)
          health = "green" if n_alerts == 0 else ("yellow" if n_alerts <= 2 else "red")

          return {
              "total_positions": len(positions),
              "total_value_usd": round(total_value, 2),
              "cluster_risks": cluster_risks,
              "alerts": alerts,
              "overall_health": health,
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
  ```

- [ ] **Schritt 6: Tests ausführen**

  ```bash
  python -m pytest tests/test_portfolio_monitor.py -v
  ```

  Erwartete Ausgabe: `4 passed`

- [ ] **Schritt 7: Commit**

  ```bash
  git add agents/portfolio/ data/portfolio.json tests/test_portfolio_monitor.py
  git commit -m "feat: add PortfolioMonitorAgent with cluster risk detection"
  ```

---

### Task 12: Drei Backtester-Agenten + background_runner.py

**Files:**
- Create: `agents/backtester/__init__.py`
- Create: `agents/backtester/top_down_backtester_agent.py`
- Create: `agents/backtester/bottom_up_backtester_agent.py`
- Create: `agents/backtester/judgment_backtester_agent.py`
- Create: `background_runner.py`
- Create: `tests/test_backtester_agents.py`

- [ ] **Schritt 1: `agents/backtester/__init__.py` erstellen** (leer)

- [ ] **Schritt 2: `agents/backtester/top_down_backtester_agent.py` erstellen**

  ```python
  from core.ports.memory_port import MemoryPort

  REGIME_CYCLE = ["Boom", "Aufschwung", "Erholung", "Abschwung", "Rezession"]

  _ADJACENT: dict[str, set] = {
      r: {
          REGIME_CYCLE[max(0, i - 1)],
          r,
          REGIME_CYCLE[min(len(REGIME_CYCLE) - 1, i + 1)],
      }
      for i, r in enumerate(REGIME_CYCLE)
  }


  def _is_adjacent(a: str, b: str) -> bool:
      return b in _ADJACENT.get(a, {a})


  def _accuracy(entries: list[dict], reference_regime: str) -> float:
      if not entries:
          return 0.0
      correct = sum(1 for e in entries if _is_adjacent(e["regime"], reference_regime))
      return round(correct / len(entries), 3)


  class TopDownBacktesterAgent:

      def __init__(self, memory: MemoryPort):
          self.memory = memory

      async def run(self) -> None:
          history = self.memory.load_global_history(days=90)
          if not history:
              print("[TopDownBacktester] Keine Einträge — übersprungen.")
              return

          # Aktuellsten Eintrag als Referenz-Regime nehmen (kein FRED-Call nötig)
          latest = max(history, key=lambda h: h["timestamp"])
          ref_regime = latest.get("regime")
          if not ref_regime:
              print("[TopDownBacktester] Kein Regime im letzten Eintrag — übersprungen.")
              return

          from datetime import datetime, timedelta, timezone
          now = datetime.now(timezone.utc)

          def entries_in_window(days: int) -> list[dict]:
              cutoff = now - timedelta(days=days)
              return [
                  h for h in history
                  if h.get("regime") and h["timestamp"] >= cutoff
              ]

          e30  = entries_in_window(30)
          e60  = entries_in_window(60)
          e90  = entries_in_window(90)

          acc30 = _accuracy(e30, ref_regime)
          acc60 = _accuracy(e60, ref_regime)
          acc90 = _accuracy(e90, ref_regime)

          report = {
              "backtester_type": "topdown",
              "ticker": None,
              "original_recommendation": None,
              "price_at_recommendation": None,
              "price_today": None,
              "return_pct": None,
              "verdict": "correct" if acc30 >= 0.70 else "incorrect",
              "accuracy_30d": acc30,
              "accuracy_60d": acc60,
              "accuracy_90d": acc90,
              "notes": (
                  f"Referenz-Regime: {ref_regime}. "
                  f"Treffsicherheit 30d={acc30:.0%} 60d={acc60:.0%} 90d={acc90:.0%}"
              ),
          }
          self.memory.save_backtester_report(report)
          print(f"[TopDownBacktester] Treffsicherheit 30d={acc30:.0%} | Regime-Referenz: {ref_regime}")
  ```

- [ ] **Schritt 3: `agents/backtester/bottom_up_backtester_agent.py` erstellen**

  ```python
  from typing import Optional
  import yfinance as yf
  from core.ports.memory_port import MemoryPort


  def _fetch_price(ticker: str) -> Optional[float]:
      try:
          return float(yf.Ticker(ticker).fast_info["last_price"])
      except Exception:
          return None


  def _verdict(signal: str, return_pct: float) -> str:
      if signal == "bullish" and return_pct >= 2.0:
          return "correct"
      if signal == "bearish" and return_pct <= -2.0:
          return "correct"
      if signal == "neutral" and abs(return_pct) <= 2.0:
          return "correct"
      if abs(return_pct) <= 1.0:
          return "neutral"
      return "incorrect"


  class BottomUpBacktesterAgent:

      def __init__(self, memory: MemoryPort):
          self.memory = memory

      async def run(self) -> None:
          history = self.memory.load_global_history(days=90)
          evaluable = [
              h for h in history
              if h.get("ticker") and h.get("dominant_signal") and h.get("price_at_analysis")
          ]
          if not evaluable:
              print("[BottomUpBacktester] Keine auswertbaren Einträge — übersprungen.")
              return

          evaluated = 0
          for entry in evaluable:
              ticker = entry["ticker"]
              price_then = float(entry["price_at_analysis"])
              signal = entry["dominant_signal"]

              price_now = _fetch_price(ticker)
              if price_now is None:
                  continue

              return_pct = ((price_now - price_then) / price_then) * 100
              verdict    = _verdict(signal, return_pct)

              self.memory.save_backtester_report({
                  "backtester_type": "bottomup",
                  "ticker": ticker,
                  "original_recommendation": signal,
                  "price_at_recommendation": price_then,
                  "price_today": price_now,
                  "return_pct": round(return_pct, 2),
                  "verdict": verdict,
                  "accuracy_30d": None,
                  "accuracy_60d": None,
                  "accuracy_90d": None,
                  "notes": f"Signal={signal} | Return={return_pct:.1f}%",
              })
              evaluated += 1

          print(f"[BottomUpBacktester] {evaluated} Einträge ausgewertet.")
  ```

- [ ] **Schritt 4: `agents/backtester/judgment_backtester_agent.py` erstellen**

  ```python
  from typing import Optional
  import yfinance as yf
  from core.ports.memory_port import MemoryPort


  def _fetch_price(ticker: str) -> Optional[float]:
      try:
          return float(yf.Ticker(ticker).fast_info["last_price"])
      except Exception:
          return None


  def _verdict(recommendation: str, return_pct: float) -> str:
      if recommendation == "BUY"  and return_pct >= 3.0:
          return "correct"
      if recommendation in ("SELL", "SHORT") and return_pct <= -3.0:
          return "correct"
      if recommendation == "HOLD" and abs(return_pct) <= 5.0:
          return "correct"
      if abs(return_pct) <= 1.5:
          return "neutral"
      return "incorrect"


  class JudgmentBacktesterAgent:

      def __init__(self, memory: MemoryPort):
          self.memory = memory

      async def run(self) -> None:
          history = self.memory.load_global_history(days=90)
          evaluable = [
              h for h in history
              if h.get("ticker") and h.get("recommendation") and h.get("price_at_analysis")
          ]
          if not evaluable:
              print("[JudgmentBacktester] Keine auswertbaren Einträge — übersprungen.")
              return

          correct = 0
          total   = 0

          for entry in evaluable:
              ticker     = entry["ticker"]
              price_then = float(entry["price_at_analysis"])
              rec        = entry["recommendation"]

              price_now = _fetch_price(ticker)
              if price_now is None:
                  continue

              return_pct = ((price_now - price_then) / price_then) * 100
              verdict    = _verdict(rec, return_pct)

              if verdict == "correct":
                  correct += 1
              total += 1

              self.memory.save_backtester_report({
                  "backtester_type": "judgment",
                  "ticker": ticker,
                  "original_recommendation": rec,
                  "price_at_recommendation": price_then,
                  "price_today": price_now,
                  "return_pct": round(return_pct, 2),
                  "verdict": verdict,
                  "accuracy_30d": None,
                  "accuracy_60d": None,
                  "accuracy_90d": None,
                  "notes": f"Empfehlung={rec} | Return={return_pct:.1f}% | Urteil={verdict}",
              })

          if total > 0:
              accuracy = round(correct / total, 3)
              # Zusammenfassungs-Report für JudgmentAgent-Kontext
              self.memory.save_backtester_report({
                  "backtester_type": "judgment",
                  "ticker": None,
                  "original_recommendation": None,
                  "price_at_recommendation": None,
                  "price_today": None,
                  "return_pct": None,
                  "verdict": "correct" if accuracy >= 0.60 else "incorrect",
                  "accuracy_30d": accuracy,
                  "accuracy_60d": None,
                  "accuracy_90d": None,
                  "notes": f"Gesamttreffsicherheit: {accuracy:.0%} aus {total} Empfehlungen",
              })
              print(f"[JudgmentBacktester] {total} ausgewertet | Treffsicherheit: {accuracy:.0%}")
  ```

- [ ] **Schritt 5: Failing-Tests für Backtester schreiben**

  `tests/test_backtester_agents.py`:

  ```python
  from agents.backtester.top_down_backtester_agent import _is_adjacent, _accuracy


  def test_adjacent_same_regime():
      assert _is_adjacent("Boom", "Boom") is True


  def test_adjacent_neighbor():
      assert _is_adjacent("Boom", "Aufschwung") is True
      assert _is_adjacent("Rezession", "Abschwung") is True


  def test_not_adjacent_far():
      assert _is_adjacent("Boom", "Rezession") is False
      assert _is_adjacent("Boom", "Abschwung") is False


  def test_accuracy_all_correct():
      entries = [{"regime": "Boom"}, {"regime": "Aufschwung"}]
      assert _accuracy(entries, "Boom") == 1.0


  def test_accuracy_none_correct():
      entries = [{"regime": "Rezession"}, {"regime": "Abschwung"}]
      assert _accuracy(entries, "Boom") == 0.0


  def test_accuracy_empty():
      assert _accuracy([], "Boom") == 0.0


  from agents.backtester.judgment_backtester_agent import _verdict as j_verdict


  def test_judgment_verdict_buy_correct():
      assert j_verdict("BUY", 5.0) == "correct"


  def test_judgment_verdict_buy_incorrect():
      assert j_verdict("BUY", -5.0) == "incorrect"


  def test_judgment_verdict_hold_correct():
      assert j_verdict("HOLD", 3.0) == "correct"


  def test_judgment_verdict_sell_correct():
      assert j_verdict("SELL", -4.0) == "correct"


  from agents.backtester.bottom_up_backtester_agent import _verdict as bu_verdict


  def test_bottomup_verdict_bullish_correct():
      assert bu_verdict("bullish", 3.0) == "correct"


  def test_bottomup_verdict_bearish_correct():
      assert bu_verdict("bearish", -3.0) == "correct"


  def test_bottomup_verdict_neutral_correct():
      assert bu_verdict("neutral", 1.0) == "correct"
  ```

- [ ] **Schritt 6: Tests ausführen**

  ```bash
  python -m pytest tests/test_backtester_agents.py -v
  ```

  Erwartete Ausgabe: `12 passed`

- [ ] **Schritt 7: `background_runner.py` erstellen**

  ```python
  import asyncio
  import os
  from dotenv import load_dotenv

  load_dotenv()

  from adapters.memory.supabase_memory import SupabaseMemory
  from agents.backtester.bottom_up_backtester_agent import BottomUpBacktesterAgent
  from agents.backtester.judgment_backtester_agent import JudgmentBacktesterAgent
  from agents.backtester.top_down_backtester_agent import TopDownBacktesterAgent
  from agents.portfolio.portfolio_monitor_agent import PortfolioMonitorAgent


  async def main() -> None:
      print("=" * 50)
      print("  AAIA Background Runner")
      print("=" * 50)

      memory = SupabaseMemory()

      agents = [
          ("TopDownBacktester",   TopDownBacktesterAgent(memory).run),
          ("BottomUpBacktester",  BottomUpBacktesterAgent(memory).run),
          ("JudgmentBacktester",  JudgmentBacktesterAgent(memory).run),
          ("PortfolioMonitor",    PortfolioMonitorAgent(memory).run),
      ]

      for name, run_fn in agents:
          print(f"\n[{name}] wird ausgeführt...")
          try:
              await run_fn()
          except Exception as e:
              print(f"[{name}] FEHLER: {e}")

      print("\n  Background Runner abgeschlossen.")
      print("=" * 50)


  if __name__ == "__main__":
      asyncio.run(main())
  ```

- [ ] **Schritt 8: Background-Runner manuell testen**

  ```bash
  python background_runner.py
  ```

  Erwartete Ausgabe (bei leerem Memory):
  ```
  ==================================================
    AAIA Background Runner
  ==================================================
  [TopDownBacktester] Keine Einträge — übersprungen.
  [BottomUpBacktester] Keine auswertbaren Einträge — übersprungen.
  [JudgmentBacktester] Keine auswertbaren Einträge — übersprungen.
  [PortfolioMonitor] Keine Positionen erfasst — übersprungen.
    Background Runner abgeschlossen.
  ==================================================
  ```

- [ ] **Schritt 9: Windows Task Scheduler einrichten**

  1. Taste `Win + R` → `taskschd.msc` → Enter
  2. Rechtsklick auf "Aufgabenplanung (Lokal)" → "Einfache Aufgabe erstellen..."
  3. Name: `AAIA Background Runner`
  4. Trigger: Täglich → 08:00 Uhr
  5. Aktion: "Programm starten"
     - Programm/Skript: `C:\Users\nicil\AppData\Local\Programs\Python\Python311\python.exe`
     - Argumente: `C:\Users\nicil\aaia_agent\background_runner.py`
     - Starten in: `C:\Users\nicil\aaia_agent`
  6. Fertig stellen → OK

  Verifikation: Rechtsklick auf die Aufgabe → "Ausführen" → Ergebnis prüfen.

- [ ] **Schritt 10: Alle Tests ausführen (Gesamtcheck)**

  ```bash
  python -m pytest tests/ -v
  ```

  Erwartete Ausgabe: `alle Tests grün` (mind. 36 Tests)

- [ ] **Schritt 11: Finaler Commit**

  ```bash
  git add agents/backtester/ background_runner.py tests/test_backtester_agents.py
  git commit -m "feat: add three backtester agents and background_runner"
  ```

- [ ] **Schritt 12: Auf GitHub pushen**

  ```bash
  git push origin master
  ```
