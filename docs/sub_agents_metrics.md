# Sub-Agents — Metriken & Kennzahlen

## MODE 1 — Market Cockpit (Top-Down)

---

### MacroChiefAgent

#### InflationAgent
| Region | Metriken | Datenquelle |
|--------|----------|-------------|
| USA | CPI, PPI, Real Rate 10Y *(Core CPI, PCE — TODO)* | FRED API |
| EU | CPI, Core CPI, PPI | EcbSdwProvider (Stub) |
| CH | CPI, Core CPI | FredSnbProvider (Stub) |

#### MoneySupplyAgent
| Region | Metriken | Datenquelle |
|--------|----------|-------------|
| USA | M2 Growth, Money Velocity (M2) | FRED API |
| EU | M2 Growth, M3 Growth | EcbSdwProvider (Stub) |
| CH | M2 Growth, M3 Growth | FredSnbProvider (Stub) |

#### InterestRateAgent
| Region | Metriken | Datenquelle |
|--------|----------|-------------|
| USA | Fed Funds Rate, Rate Direction (rising/falling/stable), Real Rate (= Fed Rate − CPI) *(Fed Balance Sheet — TODO)* | FRED API |
| EU | ECB Policy Rate, Rate Direction, Balance Sheet Growth | EcbSdwProvider (Stub) |
| CH | SNB Policy Rate, Rate Direction, Balance Sheet Growth | FredSnbProvider (Stub) |

#### GDPAgent
| Region | Metriken | Datenquelle |
|--------|----------|-------------|
| USA | GDP Growth, Industrial Production, Unemployment, Consumer Sentiment *(ISM PMI — TODO)* | FRED API |
| EU | GDP Growth, Unemployment, PMI (Composite) | EcbSdwProvider (Stub) |
| CH | GDP Growth, Unemployment *(procure.ch PMI — TODO)* | FredSnbProvider (Stub) |

#### LaborIncomeAgent
| Region | Metriken | Datenquelle |
|--------|----------|-------------|
| USA | Nominal Wage Growth, Real Wage Growth | FRED API |
| EU | *(TODO: Eurostat/ECB)* | — |
| CH | *(TODO: SNB)* | — |

#### CreditAgent
| Region | Metriken | Datenquelle |
|--------|----------|-------------|
| USA | Credit Growth, Money Velocity | FRED API |
| EU | *(TODO: ECB)* | — |
| CH | *(TODO: SNB)* | — |

#### BuffettIndicatorAgent
| Region | Metriken | Datenquelle |
|--------|----------|-------------|
| USA | Marktkapitalisierung/BIP (%), Z-Score (10J-Historie), Signal | FRED API (WILL5000INDFC + GDP) |
| ~150 Länder | Marktkapitalisierung/BIP (%), Z-Score (15J-Historie), Signal | Weltbank API (CM.MKT.LCAP.GD.ZS) |
| Global | Median aller Länder (%) | abgeleitet |

**Ausgabe:** Pro Land: `ratio_pct`, `z_score`, `year`, Signal (BULLISH < 75% / BEARISH > 135%). Nur angezeigt wenn |Z-Score| ≥ 1.5.

#### RegimeDetector *(kein Datenfetch — rechnet mit State-Dict aus MacroChiefAgent)*
| Indikator | Gewicht | Quelle |
|-----------|---------|--------|
| `gdp_growth` | 0.25 | FRED GDP |
| `unemployment` | 0.20 | FRED UNRATE |
| `inflation` | 0.15 | FRED CPIAUCSL |
| `yield_curve` (USA 10y−2y) | 0.12 | FRED T10Y2Y |
| `consumer_sentiment` | 0.10 | FRED UMCSENT |
| `industrial_production` | 0.10 | FRED INDPRO |
| `yield_curve_3m_usa` (10y−3m) | 0.08 | FRED T10Y3M |
| `fed_rate` | 0.05 | FRED FEDFUNDS |
| `yield_curve_10y2y_eu` | 0.05 | ECB SDW SR_10Y − SR_2Y |
| `yield_curve_10y3m_eu` | 0.04 | ECB SDW SR_10Y − SR_3M |
| `yield_curve_10y3m_ch` | 0.03 | FRED IRLTLT01CHM156N − IR3TIB01CHM156N |

**Ausgabe:** `MarketRegime` (BOOM / EXPANSION / SLOWDOWN / RECESSION / RECOVERY / DEPRESSION) + Konfidenz (0–1)

---

### CommodityChiefAgent (Makro)

#### EnergyAgent
- WTI Crude Oil (USD) `CL=F`
- Brent Crude Oil (USD) `BZ=F`
- Natural Gas (USD) `NG=F`

#### IndustrialMetalsAgent
- Copper (USD/lb) `HG=F`
- Aluminium (USD) `ALI=F`
- Zinc (USD) `ZNC=F`  *(FMP API: /v3/quote/ZINC)*
- Nickel (USD) `NI=F`  *(FMP API: /v3/quote/NICKEL)*

#### PreciousMetalsMacroAgent
- Gold (USD) `GC=F`
- Silver (USD) `SI=F`
- Platinum (USD) `PL=F`
- Palladium (USD) `PA=F`
- Gold/Silver Ratio
- Gold/Platinum Ratio

#### AgriculturalAgent
- Wheat (USD) `ZW=F`
- Corn (USD) `ZC=F`
- Soy (USD) `ZS=F`
- Coffee (USD) `KC=F`
- Sugar (USD) `SB=F`
- Cotton (USD) `CT=F`
- Orange Juice (USD) `OJ=F`

---

### SentimentChiefAgent

#### VIXAgent
- VIX (CBOE) `^VIX`
- VSTOXX (Euro) `^V2TX`

#### FearGreedAgent *(CNN API — TODO)*
- Fear & Greed Index (0–100)
- Label: Extreme Fear / Fear / Neutral / Greed / Extreme Greed

#### PutCallAgent
- CBOE Total Put/Call Ratio *(direkt von CBOE CSV-Datei)*

---

### YieldCurveChiefAgent

#### YieldSpreadAgent
| Region | Metriken | Datenquelle |
|--------|----------|-------------|
| USA | 10Y−2Y Spread (T10Y2Y), 10Y−3M Spread (T10Y3M), Inversion Flag, Signal | FRED API |
| EU | 10Y−2Y Spread (SR_10Y − SR_2Y), 10Y−3M Spread (SR_10Y − SR_3M), Inversion Flag, Signal | ECB SDW API *(kein API-Key)* |
| CH | 10Y−3M Spread (IRLTLT01CHM156N − IR3TIB01CHM156N), Inversion Flag, Signal *(kein 2J CH-Bond frei verfügbar — 3M SARON als Proxy)* | FRED OECD-Serien |

#### SovereignSpreadAgent
- BTP−Bund Spread (Italien−Deutschland, Basispunkte)
- OAT−Bund Spread (Frankreich−Deutschland, Basispunkte)
- Bonos−Bund Spread (Spanien−Deutschland, Basispunkte)
- Rohdaten: DE 10Y, IT 10Y, FR 10Y, ES 10Y Yields *(TODO: EcbSdwProvider vollständig anbinden)*

---

### SectorChiefAgent

#### SectorPerformanceAgent
- USA: 10 Sektor-ETF-Preise — `XLK` `XLE` `XLF` `XLV` `XLI` `XLY` `XLP` `XLB` `XLU` `XLRE`
- EU: 9 Sektor-ETF-Preise — `EXV3.DE` `EXH1.DE` `EXV1.DE` `EXV4.DE` `EXH3.DE` `EXH7.DE` `EXH4.DE` `EXV6.DE` `EXH8.DE`
- Leading Sektor (USA + EU) — 1-Monats-Rendite (%)
- Lagging Sektor (USA + EU)

#### SectorRotationAgent *(kein eigener Datenfetch)*
- Input: MarketRegime (vom MacroChiefAgent)
- Input: Leading Sektor (von SectorPerformanceAgent)
- Output: Empfohlene Sektoren, Zu-meidende Sektoren, Alignment-Flag

---

## MODE 2 — Stock Deep Dive (Bottom-Up)

---

### EquityChiefAgent *(asset_class: equity / etf)*

#### FundamentalsAgent
- P/E Ratio (Trailing), Forward P/E, PEG Ratio
- EV/EBITDA, EV/Revenue, Price/Book, Price/Sales, Price/FCF
- Dividend Yield, WACC
- Revenue CAGR 3Y, Operating Margin, Gross Margin, Debt/Equity

#### QualityAgent
- Gross/Operating/Net/FCF Margin
- ROE, ROA, ROIC
- Debt/Equity, Net Debt/EBITDA, Interest Coverage
- Current Ratio, Altman Z-Score

#### ShortInterestAgent
- Short Float %, Days to Cover

#### InsiderAgent
- Net Direction (net_buy / net_sell / neutral)
- Anzahl Transaktionen (Käufe vs. Verkäufe, letzte Periode)

#### EarningsTrendAgent
- Beat Rate (Anteil Quartale mit Actual > Estimate)
- Estimate Revision (up / down / flat — Durchschnitt letzte 2 Quartale)

#### MoatAgent *(LLM-basiert, Claude)*
- Intangible Assets, Switching Costs, Network Effects, Cost Advantages, Efficient Scale (je 0–2)
- Total Moat Score (0–10) → wide / narrow / none

#### ValuationRangeAgent
- KGV-Multiple: EPS × Sektor-P/E-Bandbreite (low/high)
- EV/EBITDA-Multiple: EBITDA/Share × Sektor-Bandbreite − Net Debt/Share
- DCF (vereinfacht): FCF/Share, WACC, Revenue CAGR 3Y, Terminal Growth (2.5%)
- Position: undervalued / fair / overvalued

---

### BondChiefAgent *(asset_class: bond)*

#### BondMetricsAgent
- YTM, YTC, Current Yield (= Coupon / Preis), Real Yield (= YTM − CPI)
- Coupon, Preis, Restlaufzeit (Jahre), Breakeven Inflation

#### BondDurationAgent
- Macaulay Duration, Modified Duration, Convexity, DV01

#### BondCreditAgent
- Moody's / S&P / Fitch Rating
- Kategorie: investment_grade / high_yield / junk
- Rating-Trend: upgrade / downgrade / stable
- Default-Wahrscheinlichkeit (historische Moody's-Ausfallraten)

#### BondSpreadAgent
- Spread (Basispunkte vs. Benchmark), OAS, Z-Spread
- Spread-Trend: tightening / widening / stable

---

### IndexChiefAgent *(asset_class: index / etf)*

#### IndexPriceAgent
- Aktueller Preis, Performance: 1W / 1M / 3M / YTD / 1Y / 3Y / 5Y (%)
- 52W-Hoch, 52W-Tief

#### IndexValuationAgent
- P/E Trailing, P/E Forward, Dividend Yield, EV/EBITDA

#### IndexEarningsAgent
- EPS Growth 1Y (%), Revenue Growth 1Y (%), Operating Margin (%)
- Estimate Revision (Proxy: Forward PE vs. Trailing PE)

#### IndexBreadthAgent *(Stub — TODO)*
- % Aktien über MA50 / MA200, Advance/Decline Ratio, New Highs/Lows

#### IndexMomentumAgent
- RSI-14, MA50, MA200, Golden Cross Flag (MA50 > MA200)
- Relative Strength vs. MSCI World (URTH)

#### SectorCompositionAgent
- Top Sektor (Name + Gewicht %), Top Holding (Name + Gewicht %)
- Top-10-Konzentration *(TODO: ETF Holdings API)*

#### IndexValuationRangeAgent
- EPS Estimate (Trailing/Forward)
- Historische P/E-Bandbreite Low/Mid/High (index-spezifisch)
- Preisziel Low/Mid/High (= EPS × P/E-Bandbreite), Position: undervalued / fair / overvalued

---

### CommodityChiefAgent (Deep Dive) *(asset_class: commodity)*

#### SupplyDemandAgent
- Lagerbestände aktuell + 5J-Durchschnitt + % vs. 5J-Durchschnitt
- Produktionsveränderung YoY, Stock-to-Flow (S2F), S2F-Label

#### SeasonalityAgent
- Monatlicher Bias (bullish / neutral / bearish)
- Durchschnittliche Monatsrendite (10J-Historie), Anteil positiver Jahre

#### COTAgent *(Stub — TODO: CFTC API)*
- Netto-Spekulative-Long-Position, Netto-Spekulativ % des Open Interest

#### CommodityValuationRangeAgent
- 5J-Preistief / 5J-Preishoch / 5J-Perzentil / 10J-Perzentil
- Position: cheap / fair / expensive

---

### PreciousMetalsChiefAgent *(asset_class: precious_metal)*

#### PreciousMetalPriceAgent
- Aktueller Preis (USD), Stock-to-Flow: Gold 62 / Silver 22 / Platinum 0.4 / Palladium 0.5
- *(Performance, RSI, MA50, MA200, Realzins-Korrelation — TODO)*

#### CrossMetalAgent
- Gold/Silver Ratio (historischer Durchschnitt: 68)
- Gold/Platinum Ratio (historischer Durchschnitt: 1.0)

#### PreciousMetalsValuationAgent
- Realzins-Modell: Real Rate 10Y → Preisanpassung (~±$150 je 1%)
- Inflationsbereinigt: historischer Gold-Durchschnitt ($1'200 Basis)
- S2F Produktionskosten-Boden: AISC günstigster ($1'050) / teuerster ($1'800) Produzent
- Position: undervalued / fair / overvalued

---

## MODE 3 — Judgment (Kombinations-Urteil)

### AnomalyChiefAgent

#### TopDownAnomalyAgent *(kein eigener Datenfetch — liest CockpitResult)*
- Statistische Prüfung (Z-Score vs. 90-Tage-Historie): VIX, Fear & Greed, Yield Spread, CPI
- Yield Spread marktspezifisch: `market="CH"` → Schweizer Kurve, `market="DE"` → Eurozone, `market="USA"` → USA
- Buffett-Indikator Z-Score (nur für equity/etf/index)
- Regime-Konfidenz < 30% → Anomalie
- Widerspruchs-Checks: Macro vs. Sentiment, Macro vs. YieldCurve, Commodity vs. Macro

#### BottomUpAnomalyAgent *(kein eigener Datenfetch — liest BottomUpResult)*
- Statistische Prüfung: KGV, Short Float %
- Widerspruchs-Checks: Fundamentals vs. Valuation, Earnings vs. Quality

### JudgmentChiefAgent *(LLM: Claude)*
- Input: Top-Down-Kontext, Bottom-Up-Analyse, Anomalie-Bericht, Backtester-Kontext
- Output: Empfehlung (KAUFEN / HALTEN / VERKAUFEN / BEOBACHTEN), Begründung, Risiken

### BacktesterChiefAgent *(Memory: Supabase)*
- Lädt vergangene Analysen (90 Tage), bewertet Trefferquote früherer Empfehlungen

---

## Datenquellen-Übersicht

| Provider | API | Verwendet von |
|----------|-----|---------------|
| `FredDataProvider` | FRED API (St. Louis Fed) | MacroChiefAgent, YieldSpreadAgent (USA), BuffettIndicatorAgent |
| `EcbSdwProvider` | ECB Statistical Data Warehouse *(kein Key)* | YieldSpreadAgent (EU), MacroChiefAgent (EU Spreads) |
| `FredSnbProvider` | FRED OECD-Serien | YieldSpreadAgent (CH), MacroChiefAgent (CH Spreads) |
| `YahooFinanceProvider` | Yahoo Finance / yfinance | CommodityChiefAgent, SentimentChiefAgent, SectorChiefAgent, alle DeepDive-Agents |
| `FinnhubProvider` | Finnhub API | FundamentalsAgent, QualityAgent, InsiderAgent, BondCreditAgent |
| `FmpDataProvider` | Financial Modeling Prep | IndexValuationAgent, Shiller CAPE EU/CH |
| Weltbank API | World Bank Open Data *(kein Key)* | BuffettIndicatorAgent (150 Länder) |
| CBOE CSV | cboe.com *(kein Key)* | PutCallAgent |
| LLMProvider | Anthropic Claude API | MoatAgent, JudgmentAgent |

---

## Architektur-Übersicht

```
AAIA — Agentensystem
═══════════════════════════════════════════════════════════════════

MODE 1: MARKET COCKPIT (Top-Down)
──────────────────────────────────────────────────────────────────
TopDownOrchestrator
│
├── MacroChiefAgent ◄─── FredDataProvider, EcbSdwProvider, FredSnbProvider
│   │
│   ├── InflationAgent ........... CPI, PPI, Real Rate
│   ├── MoneySupplyAgent ......... M2, M3, Money Velocity
│   ├── InterestRateAgent ........ Leitzins, Rate Direction, Real Rate
│   ├── GDPAgent ................. BIP, Industrie, Arbeitslosigkeit, Sentiment
│   ├── LaborIncomeAgent ......... Nominallohn, Reallohn
│   ├── CreditAgent .............. Kreditwachstum, Money Velocity
│   ├── BuffettIndicatorAgent .... Marktkapitalisierung/BIP, Z-Score, 150 Länder
│   │     └── Quellen: FRED + Weltbank API
│   │
│   └── RegimeDetector (kein Agent — pure Logik)
│         Inputs:  gdp 0.25 | unemployment 0.20 | inflation 0.15
│                  yield_10y2y_usa 0.12 | sentiment 0.10 | indprod 0.10
│                  yield_3m_usa 0.08 | fed_rate 0.05
│                  yield_10y2y_eu 0.05 | yield_10y3m_eu 0.04 | yield_10y3m_ch 0.03
│         Output: MarketRegime + Konfidenz (0–1)
│
├── CommodityChiefAgent (Makro) ◄─── YahooFinanceProvider, FmpDataProvider
│   ├── EnergyAgent .............. WTI, Brent, Natural Gas
│   ├── IndustrialMetalsAgent .... Copper, Aluminium, Zinc, Nickel
│   ├── PreciousMetalsMacroAgent . Gold, Silver, Platinum, Palladium
│   └── AgriculturalAgent ........ Wheat, Corn, Soy, Coffee, Sugar, Cotton, OJ
│
├── SentimentChiefAgent ◄─── YahooFinanceProvider, CBOE CSV
│   ├── VIXAgent ................. VIX (USA), VSTOXX (EU)
│   ├── FearGreedAgent ........... Index 0–100  (TODO: CNN API)
│   └── PutCallAgent ............. CBOE Put/Call Ratio
│
├── YieldCurveChiefAgent
│   ├── YieldSpreadAgent ◄─── FredDataProvider + EcbSdwProvider + FredSnbProvider
│   │     USA: T10Y2Y + T10Y3M          (FRED)
│   │     EU:  SR_10Y − SR_2Y/3M       (ECB SDW)
│   │     CH:  10Y − 3M SARON          (FRED OECD)
│   │     Ausgabe: Spread, Inversion Flag, Signal pro Region
│   │
│   └── SovereignSpreadAgent ◄─── EcbSdwProvider (TODO: vollständig anbinden)
│         IT−DE / FR−DE / ES−DE Spreads (Basispunkte)
│
└── SectorChiefAgent ◄─── YahooFinanceProvider
    ├── SectorPerformanceAgent ... 10 USA-ETFs + 9 EU-ETFs, 1M-Rendite (%)
    └── SectorRotationAgent ...... Empfehlung basierend auf Regime + Leading-Sektor


MODE 2: STOCK DEEP DIVE (Bottom-Up)  —  asset_class bestimmt den Chief
──────────────────────────────────────────────────────────────────
BottomUpOrchestrator
│
├── EquityChiefAgent ◄─── YahooFinanceProvider + FinnhubProvider
│   asset_class: equity / etf
│   ├── FundamentalsAgent ........ PE, PEG, EV/EBITDA, Margen, Debt/Equity
│   ├── QualityAgent ............. Margen, ROE/ROA/ROIC, Altman Z-Score
│   ├── ShortInterestAgent ....... Short Float %, Days to Cover
│   ├── InsiderAgent ............. Net Direction, Transaktionsanzahl
│   ├── EarningsTrendAgent ....... Beat Rate, Estimate Revision
│   ├── MoatAgent ................ Moat-Score 0–10  (LLM: Claude)
│   └── ValuationRangeAgent ...... KGV / EV/EBITDA / DCF → Fair Value Range
│
├── BondChiefAgent ◄─── YahooFinanceProvider + FinnhubProvider
│   asset_class: bond
│   ├── BondMetricsAgent ......... YTM, YTC, Current Yield, Real Yield
│   ├── BondDurationAgent ........ Macaulay / Modified Duration, Convexity, DV01
│   ├── BondCreditAgent .......... Moody's/S&P/Fitch, Default-Wahrscheinlichkeit
│   └── BondSpreadAgent .......... Spread, OAS, Z-Spread
│
├── IndexChiefAgent ◄─── YahooFinanceProvider + FmpDataProvider
│   asset_class: index / etf
│   ├── IndexPriceAgent .......... Preis, Performance 1W–5Y, 52W-Hoch/Tief
│   ├── IndexValuationAgent ...... PE Trailing/Forward, Div. Yield, EV/EBITDA
│   ├── IndexEarningsAgent ....... EPS/Revenue Growth, Margin, Estimate Revision
│   ├── IndexBreadthAgent ........ MA50/200 %, A/D Ratio  (TODO: Datenquellen)
│   ├── IndexMomentumAgent ....... RSI-14, MA50/200, Golden Cross, Rel. Strength
│   ├── SectorCompositionAgent ... Top Sektor + Holding, Konzentration
│   └── IndexValuationRangeAgent . P/E Bandbreite → Preisziel Low/Mid/High
│
├── CommodityChiefAgent (Deep Dive) ◄─── YahooFinanceProvider
│   asset_class: commodity
│   ├── SupplyDemandAgent ........ Lagerbestände, S2F, Produktionsveränderung
│   ├── SeasonalityAgent ......... Monatlicher Bias, Ø-Rendite, % positive Jahre
│   ├── COTAgent ................. Spekulative Positionierung  (TODO: CFTC API)
│   └── CommodityValuationRangeAgent  5J/10J-Perzentil, cheap/fair/expensive
│
└── PreciousMetalsChiefAgent ◄─── YahooFinanceProvider
    asset_class: precious_metal
    ├── PreciousMetalPriceAgent .. Preis, Stock-to-Flow
    ├── CrossMetalAgent .......... Gold/Silver, Gold/Platinum Ratio
    └── PreciousMetalsValuationAgent  Realzins / CPI / S2F → Fair Value Range


MODE 3: JUDGMENT (Kombinations-Urteil)
──────────────────────────────────────────────────────────────────
JudgmentOrchestrator
│   Input: CockpitResult (Mode 1) + BottomUpResult (Mode 2) + market
│
├── AnomalyChiefAgent
│   ├── TopDownAnomalyAgent ◄─── CockpitResult
│   │     Statistisch: VIX, Fear&Greed, Yield Spread*, CPI, Buffett Z-Score
│   │     *marktspezifisch: CH → schweizer Kurve | EU → Eurozone | USA → USA
│   │     Widersprüche: Macro↔Sentiment, Macro↔YieldCurve, Commodity↔Macro
│   └── BottomUpAnomalyAgent ◄─── BottomUpResult
│         Statistisch: KGV, Short Float %
│         Widersprüche: Fundamentals↔Valuation, Earnings↔Quality
│
├── JudgmentChiefAgent ◄─── LLMProvider (Claude)
│   └── JudgmentAgent ........... KAUFEN / HALTEN / VERKAUFEN / BEOBACHTEN
│         Prompt: Top-Down-Kontext + Bottom-Up + Anomalien + Backtester
│
└── BacktesterChiefAgent ◄─── Supabase Memory
    ├── TopDownBacktesterAgent ... Trefferquote Regime-Prognosen
    ├── BottomUpBacktesterAgent .. Trefferquote Stock-Bewertungen
    └── JudgmentBacktesterAgent .. Trefferquote Kauf/Verkauf-Empfehlungen


DATENFLUSS
──────────────────────────────────────────────────────────────────

  FRED API ──────────────────────────► MacroChiefAgent (USA Makro)
                                    ► YieldSpreadAgent (USA T10Y2Y, T10Y3M)
                                    ► BuffettIndicatorAgent (USA)
                                    ► MacroChiefAgent (CH Spreads via OECD)
                                    ► YieldSpreadAgent (CH via OECD)

  ECB SDW API ────────────────────────► YieldSpreadAgent (EU SR_10Y/2Y/3M)
  (kein Key)                          ► MacroChiefAgent (EU Spreads)

  Weltbank API ───────────────────────► BuffettIndicatorAgent (150 Länder)
  (kein Key)

  Yahoo Finance ──────────────────────► CommodityChiefAgent (alle Preise)
                                      ► SentimentChiefAgent (VIX, VSTOXX)
                                      ► SectorChiefAgent (Sektor-ETFs)
                                      ► alle DeepDive-Agents (Preis, History)

  CBOE CSV ───────────────────────────► PutCallAgent
  (kein Key)

  Finnhub API ────────────────────────► FundamentalsAgent, InsiderAgent
                                      ► BondCreditAgent, ShortInterestAgent

  FMP API ────────────────────────────► IndexValuationAgent
  (Financial Modeling Prep)           ► Shiller CAPE EU/CH

  Claude (LLM) ───────────────────────► MoatAgent, JudgmentAgent
```
