# Sub-Agents — Metriken & Kennzahlen

## MODE 1 — Market Cockpit (Top-Down)

---

### MacroChiefAgent

#### InflationAgent
| Region | Metriken |
|--------|----------|
| USA | CPI, PPI, Real Rate 10Y *(Core CPI, PCE — TODO)* |
| EU | CPI, Core CPI, PPI |
| CH | CPI, Core CPI |

#### MoneySupplyAgent
| Region | Metriken |
|--------|----------|
| USA | M2 Growth, Money Velocity (M2) |
| EU | M2 Growth, M3 Growth |
| CH | M2 Growth, M3 Growth |

#### InterestRateAgent
| Region | Metriken |
|--------|----------|
| USA | Fed Funds Rate, Rate Direction (rising/falling/stable), Real Rate (= Fed Rate − CPI) *(Fed Balance Sheet — TODO)* |
| EU | ECB Policy Rate, Rate Direction, Balance Sheet Growth |
| CH | SNB Policy Rate, Rate Direction, Balance Sheet Growth |

#### GDPAgent
| Region | Metriken |
|--------|----------|
| USA | GDP Growth, Industrial Production, Unemployment, Consumer Sentiment *(ISM PMI — TODO)* |
| EU | GDP Growth, Unemployment, PMI (Composite) |
| CH | GDP Growth, Unemployment *(procure.ch PMI — TODO)* |

#### ShillerCAPEAgent *(Datenquellen alle TODO)*
| Region | Metriken |
|--------|----------|
| USA | Shiller CAPE, Historical Average (17.0), Deviation % |
| EU | Shiller CAPE, Historical Average (15.0), Deviation % |
| CH | Shiller CAPE, Historical Average (18.0), Deviation % |

#### LaborIncomeAgent
| Region | Metriken |
|--------|----------|
| USA | Nominal Wage Growth, Real Wage Growth |
| EU | *(TODO: Eurostat/ECB)* |
| CH | *(TODO: SNB)* |

#### CreditAgent
| Region | Metriken |
|--------|----------|
| USA | Credit Growth, Money Velocity |
| EU | *(TODO: ECB)* |
| CH | *(TODO: SNB)* |

---

### CommodityChiefAgent (Makro)

#### EnergyAgent
- WTI Crude Oil (USD) `CL=F`
- Brent Crude Oil (USD) `BZ=F`
- Natural Gas (USD) `NG=F`

#### IndustrialMetalsAgent
- Copper (USD/lb) `HG=F`
- Aluminium (USD) `ALI=F`
- Zinc (USD) `ZNC=F`
- Nickel (USD) `NI=F`

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
- CBOE Total Put/Call Ratio `^PCALL`

---

### YieldCurveChiefAgent

#### YieldSpreadAgent
| Region | Metriken |
|--------|----------|
| USA | 10Y−2Y Spread (T10Y2Y), 10Y−3M Spread (T10Y3M), Inversion Flag |
| EU | *(TODO: Bund Yields)* |
| CH | 10Y−2Y Spread (SNB Sovereign Yields) |

#### SovereignSpreadAgent
- BTP−Bund Spread (Italien−Deutschland, Basispunkte)
- OAT−Bund Spread (Frankreich−Deutschland, Basispunkte)
- Bonos−Bund Spread (Spanien−Deutschland, Basispunkte)
- Rohdaten: DE 10Y, IT 10Y, FR 10Y, ES 10Y Yields

---

### SectorChiefAgent

#### SectorPerformanceAgent
- USA: 10 Sektor-ETF-Preise — `XLK` `XLE` `XLF` `XLV` `XLI` `XLY` `XLP` `XLB` `XLU` `XLRE`
- EU: 9 Sektor-ETF-Preise — `EXV3.DE` `EXH1.DE` `EXV1.DE` `EXV4.DE` `EXH3.DE` `EXH7.DE` `EXH4.DE` `EXV6.DE` `EXH8.DE`
- Leading Sektor (USA + EU)
- Lagging Sektor (USA + EU)

#### SectorRotationAgent *(kein eigener Datenfetch)*
- Input: MarketRegime (BOOM / EXPANSION / SLOWDOWN / RECESSION / RECOVERY)
- Input: Leading Sektor von SectorPerformanceAgent
- Output: Empfohlene Sektoren, Zu-meidende Sektoren, Alignment-Flag

---

## MODE 2 — Stock Deep Dive (Bottom-Up)

---

### EquityChiefAgent

#### FundamentalsAgent
- P/E Ratio (Trailing)
- Forward P/E
- Shiller CAPE (Einzelaktie)
- PEG Ratio
- EV/EBITDA
- EV/Revenue
- Price/Book
- Price/Sales
- Price/FCF
- Dividend Yield
- WACC
- Revenue CAGR 3Y
- Operating Margin
- Gross Margin
- Debt/Equity

#### QualityAgent
- Gross Margin
- Operating Margin
- Net Margin
- FCF Margin
- ROE
- ROA
- ROIC
- Debt/Equity
- Net Debt/EBITDA
- Interest Coverage
- Current Ratio
- Altman Z-Score

#### ShortInterestAgent
- Short Float %
- Days to Cover

#### InsiderAgent
- Net Direction (net_buy / net_sell / neutral)
- Anzahl Transaktionen (Käufe vs. Verkäufe, letzte Periode)

#### EarningsTrendAgent
- Beat Rate (Anteil Quartale mit Actual > Estimate)
- Estimate Revision (up / down / flat — Durchschnitt letzte 2 Quartale)

#### MoatAgent *(LLM-basiert)*
- Intangible Assets Score (0–2)
- Switching Costs Score (0–2)
- Network Effects Score (0–2)
- Cost Advantages Score (0–2)
- Efficient Scale Score (0–2)
- Total Moat Score (0–10)
- Overall: wide / narrow / none

#### ValuationRangeAgent
- KGV-Multiple: EPS × Sektor-P/E-Bandbreite (low/high)
- EV/EBITDA-Multiple: EBITDA/Share × Sektor-Bandbreite − Net Debt/Share
- DCF (vereinfacht): FCF/Share, WACC, Revenue CAGR 3Y, Terminal Growth (2.5%)
- Aktueller Preis vs. kombinierter Bewertungsrange
- Position: undervalued / fair / overvalued

---

### BondChiefAgent

#### BondMetricsAgent
- Yield to Maturity (YTM)
- Yield to Call (YTC)
- Current Yield (= Coupon / Preis)
- Real Yield (= YTM − CPI)
- Coupon
- Aktueller Preis
- Restlaufzeit (Jahre)
- Breakeven Inflation
- Land *(Staatsanleihen)*
- Emittent + Sektor *(Unternehmensanleihen)*

#### BondDurationAgent
- Macaulay Duration
- Modified Duration
- Convexity
- DV01 (= Modified Duration × Preis × 0.0001)

#### BondCreditAgent
- Moody's Rating
- S&P Rating
- Fitch Rating
- Kategorie: investment_grade / high_yield / junk
- Rating-Trend: upgrade / downgrade / stable
- Default-Wahrscheinlichkeit (aus Moody's historischen Ausfallraten)

#### BondSpreadAgent
- Spread (Basispunkte vs. Benchmark)
- OAS (Option-Adjusted Spread)
- Z-Spread
- Spread-Trend: tightening / widening / stable

---

### IndexChiefAgent

#### IndexPriceAgent
- Aktueller Preis
- Performance: 1W, 1M, 3M, YTD, 1Y, 3Y, 5Y (%)
- 52-Wochen-Hoch
- 52-Wochen-Tief

#### IndexValuationAgent
- P/E Trailing
- P/E Forward
- Shiller CAPE *(TODO)*
- Dividend Yield
- EV/EBITDA

#### IndexEarningsAgent
- EPS Growth 1Y (%)
- Revenue Growth 1Y (%)
- Operating Margin (%)
- Estimate Revision (Proxy: Veränderung Forward PE vs. Trailing PE)

#### IndexBreadthAgent *(Stub — TODO: Datenquellen)*
- % Aktien über MA50
- % Aktien über MA200
- Advance/Decline Ratio
- New Highs
- New Lows

#### IndexMomentumAgent
- RSI-14
- MA50
- MA200
- Golden Cross Flag (MA50 > MA200)
- Relative Strength vs. MSCI World (URTH)

#### SectorCompositionAgent
- Top Sektor (Name + Gewicht %)
- Top Holding (Name + Gewicht %)
- Top-10-Konzentration *(TODO: ETF Holdings API)*

#### IndexValuationRangeAgent
- EPS Estimate (Trailing/Forward)
- Historische P/E-Bandbreite Low/Mid/High (index-spezifisch)
- Preisziel Low/Mid/High (= EPS × P/E-Bandbreite)
- Aktueller Preis vs. Range
- Position: undervalued / fair / overvalued

---

### CommodityChiefAgent (Deep Dive)

#### SupplyDemandAgent
- Lagerbestände aktuell
- Lagerbestand 5J-Durchschnitt
- Lagerbestand % vs. 5J-Durchschnitt
- Produktionsveränderung YoY
- Stock-to-Flow (S2F) Ratio
- S2F-Label: scarce / normal / abundant

#### SeasonalityAgent
- Monatlicher Bias (bullish / neutral / bearish)
- Durchschnittliche Monatsrendite (aktueller Monat, 10J-Historie)
- Anteil positiver Jahre (% des aktuellen Monats)

#### COTAgent *(Stub — TODO: CFTC API)*
- Netto-Spekulative-Long-Position
- Netto-Spekulativ % des Open Interest

#### CommodityValuationRangeAgent
- Aktueller Preis
- 5J-Preistief / 5J-Preishoch
- 5J-Perzentil (Position in 5J-Range)
- 10J-Perzentil
- Produktionskosten Low/High *(TODO)*
- Position: cheap / fair / expensive

---

### PreciousMetalsChiefAgent

#### PreciousMetalPriceAgent
- Aktueller Preis (USD)
- Performance 1W / 1M / 3M / 1Y / 5Y *(TODO)*
- RSI *(TODO)*
- MA50 *(TODO)*
- MA200 *(TODO)*
- Stock-to-Flow: Gold 62 / Silver 22 / Platinum 0.4 / Palladium 0.5
- Realzins-Korrelation *(TODO)*

#### CrossMetalAgent
- Gold/Silver Ratio (historischer Durchschnitt: 68)
- Gold/Platinum Ratio (historischer Durchschnitt: 1.0)

#### PreciousMetalsValuationAgent
- Methode 1 — Realzins-Modell: Real Rate 10Y → Preisanpassung (ca. ±$150 je 1%)
- Methode 2 — Inflationsbereinigt: historischer Gold-Durchschnitt ($1'200 Basis)
- Methode 3 — S2F Produktionskosten-Boden: AISC günstigster Produzent ($1'050) / teuerster ($1'800)
- Aktueller Preis vs. kombinierter Range
- Position: undervalued / fair / overvalued
