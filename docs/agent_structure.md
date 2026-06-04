agents/
│
├── anomaly_chief_agent.py
├── backtester_chief_agent.py
├── judgment_chief_agent.py
│
├── anomaly/
│   ├── top_down_anomaly_agent.py
│   └── bottom_up_anomaly_agent.py
│
├── backtester/
│   ├── top_down_backtester_agent.py
│   ├── bottom_up_backtester_agent.py
│   └── judgment_backtester_agent.py
│
├── judgment/
│   └── judgment_agent.py
│
├── portfolio/
│   └── portfolio_monitor_agent.py
│
├── market_cockpit/
│   ├── macro_chief_agent.py
│   ├── commodity_chief_agent_makro.py
│   ├── sentiment_chief_agent.py
│   ├── yield_curve_chief_agent.py
│   ├── sector_chief_agent.py
│   │
│   ├── macro/
│   │   ├── gdp_agent.py
│   │   ├── inflation_agent.py
│   │   ├── interest_rate_agent.py
│   │   ├── credit_agent.py
│   │   ├── labor_income_agent.py
│   │   ├── money_supply_agent.py
│   │   └── shiller_cape_agent.py
│   │
│   ├── commodity/
│   │   ├── energy_agent.py
│   │   ├── industrial_metals_agent.py
│   │   ├── precious_metals_macro_agent.py
│   │   └── agricultural_agent.py
│   │
│   ├── sentiment/
│   │   ├── vix_agent.py
│   │   ├── fear_greed_agent.py
│   │   └── put_call_agent.py
│   │
│   ├── yield_curve/
│   │   ├── yield_spread_agent.py
│   │   └── sovereign_spread_agent.py
│   │
│   └── sector/
│       ├── sector_performance_agent.py
│       └── sector_rotation_agent.py
│
└── stock_deep_dive/
    ├── equity_chief_agent.py
    ├── bond_chief_agent.py
    ├── index_chief_agent.py
    ├── commodity_chief_agent_mikro.py
    ├── precious_metals_chief_agent.py
    │
    ├── equity/
    │   ├── fundamentals_agent.py
    │   ├── quality_agent.py
    │   ├── short_interest_agent.py
    │   ├── insider_agent.py
    │   ├── earnings_trend_agent.py
    │   ├── moat_agent.py
    │   └── valuation_range_agent.py
    │
    ├── bond/
    │   ├── bond_metrics_agent.py
    │   ├── bond_duration_agent.py
    │   ├── bond_credit_agent.py
    │   └── bond_spread_agent.py
    │
    ├── index/
    │   ├── index_price_agent.py
    │   ├── index_valuation_agent.py
    │   ├── index_earnings_agent.py
    │   ├── index_breadth_agent.py
    │   ├── index_momentum_agent.py
    │   ├── index_valuation_range_agent.py
    │   └── sector_composition_agent.py
    │
    ├── commodity/
    │   ├── supply_demand_agent.py
    │   ├── seasonality_agent.py
    │   ├── cot_agent.py
    │   └── commodity_valuation_range_agent.py
    │
    └── precious_metals/
        ├── precious_metal_price_agent.py
        ├── cross_metal_agent.py
        └── precious_metals_valuation_agent.py
