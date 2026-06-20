-- =============================================================================
-- AAIA — Datenbank-Schema (Supabase / PostgreSQL)
-- =============================================================================
--
-- ⚠️  PROVISORISCH — AUS DEM ANWENDUNGSCODE REKONSTRUIERT (2026-06-20).
--
--     Diese Datei ist KEINE autoritative Quelle. Die SPALTENNAMEN stammen exakt
--     aus den SQL-Statements in `adapters/memory/supabase_memory.py`, aber
--     TYPEN, PRIMARY KEYS, DEFAULTS, INDIZES und die `id`/`timestamp`-Spalten
--     sind BEGRÜNDETE SCHÄTZUNGEN — sie konnten nicht gegen die echte DB geprüft
--     werden (kein DB-Zugriff zur Erstellungszeit).
--
--     → Vor Verlass im Ernstfall (Wiederherstellung/Umzug) durch den ECHTEN Dump
--       ersetzen. Autoritativ erzeugen mit:
--           pg_dump --schema-only --no-owner "$SUPABASE_DB_URL" > db/schema.sql
--       (oder im Supabase-Dashboard: Database → Schema/Backups exportieren).
--
-- Tabellen, die der Code anfasst (supabase_memory.py):
--   - analysis_memory     (save_analysis / load_history / load_global_history)
--   - backtester_reports  (save_backtester_report / load_latest_backtester_report)
--   - portfolio_snapshots (save_portfolio_snapshot / load_latest_portfolio_snapshot)
-- =============================================================================


-- ── analysis_memory ─────────────────────────────────────────────────────────
-- Eine Zeile je gespeicherter Analyse (judgment-Pfad).
CREATE TABLE IF NOT EXISTS analysis_memory (
    id                          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  -- (geschätzt)
    timestamp                   timestamptz NOT NULL DEFAULT now(),               -- (genutzt in WHERE/ORDER BY)
    ticker                      text,
    asset_class                 text,
    market                      text,
    regime                      text,
    regime_confidence           double precision,
    top_down_context            text,
    alignment                   text,
    dominant_signal             text,
    recommendation              text,   -- Long-Aktion (BUY/BUY+/HOLD/SELL/NONE)
    short_action                text,   -- Short-Aktion (SHORT/SHORT+/HOLD/COVER/NONE) — separat, da Long-Linse bei Short auf NONE deferiert
    confidence                  double precision,
    xai_explanation             text,
    price_at_analysis           double precision,
    top_down_anomaly_severity   text,
    bottom_up_anomaly_severity  text,
    indicators_snapshot         jsonb   -- (json.dumps(...) im Code; jsonb geschätzt)
);
CREATE INDEX IF NOT EXISTS idx_analysis_memory_ticker_ts ON analysis_memory (ticker, timestamp DESC);  -- (geschätzt; load_history filtert ticker+timestamp)


-- ── backtester_reports ──────────────────────────────────────────────────────
-- Eine Zeile je Backtester-Report.
CREATE TABLE IF NOT EXISTS backtester_reports (
    id                       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  -- (geschätzt)
    timestamp                timestamptz NOT NULL DEFAULT now(),               -- (genutzt in WHERE/ORDER BY)
    backtester_type          text,
    ticker                   text,
    original_recommendation  text,
    price_at_recommendation  double precision,
    price_today              double precision,
    return_pct               double precision,
    verdict                  text,
    accuracy_30d             double precision,
    accuracy_60d             double precision,
    accuracy_90d             double precision,
    notes                    text
);
CREATE INDEX IF NOT EXISTS idx_backtester_reports_type_ts ON backtester_reports (backtester_type, timestamp DESC);  -- (geschätzt)


-- ── portfolio_snapshots ─────────────────────────────────────────────────────
-- Eine Zeile je Portfolio-Monitor-Lauf.
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  -- (geschätzt)
    timestamp         timestamptz NOT NULL DEFAULT now(),               -- (genutzt in ORDER BY)
    total_positions   integer,
    total_value_usd   double precision,
    cluster_risks     jsonb,   -- (json.dumps(...) im Code; jsonb geschätzt)
    alerts            jsonb,   -- (json.dumps(...) im Code; jsonb geschätzt)
    overall_health    text
);


-- =============================================================================
-- Migrationshistorie (manuell gepflegt, bis ein echtes Migrations-Tool existiert)
-- =============================================================================
-- 2026-06-20  analysis_memory: Spalte short_action ergänzt (PR #9 / Block 3a F1-Nachbesserung).
--             ALTER TABLE analysis_memory ADD COLUMN IF NOT EXISTS short_action text;
