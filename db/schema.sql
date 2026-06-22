-- =============================================================================
-- AAIA — Datenbank-Schema (Supabase / PostgreSQL)
-- =============================================================================
--
-- AUTORITATIV — am 2026-06-20 aus der laufenden Supabase-DB exportiert
-- (via information_schema.columns + pg_indexes; Typen/Defaults/PKs verifiziert).
--
-- Neu erzeugen (z. B. nach Schema-Änderungen) — autoritativste Quelle:
--     pg_dump --schema-only --no-owner "$SUPABASE_DB_URL" > db/schema.sql
--
-- Tabellen, die der Code anfasst (adapters/memory/supabase_memory.py):
--   - analysis_memory     (save_analysis / load_history / load_global_history)
--   - backtester_reports  (save_backtester_report / load_latest_backtester_report)
--   - portfolio_snapshots (save_portfolio_snapshot / load_latest_portfolio_snapshot)
--
-- Hinweis: Es existieren nur die PRIMARY-KEY-Indizes (auf id). Auf den
-- Lese-Filtern (analysis_memory.ticker+timestamp, backtester_reports.backtester_type
-- +timestamp) gibt es KEINE Indizes — siehe Folge-Aufgabe in docs/open_todos.md §7.
-- =============================================================================


-- ── analysis_memory ─────────────────────────────────────────────────────────
-- Eine Zeile je gespeicherter Analyse (judgment-Pfad).
CREATE TABLE IF NOT EXISTS analysis_memory (
    id                          uuid              NOT NULL DEFAULT gen_random_uuid(),
    timestamp                   timestamptz       NOT NULL DEFAULT now(),
    ticker                      varchar           NOT NULL,
    asset_class                 varchar           NOT NULL,
    market                      varchar           NOT NULL,
    regime                      varchar,
    regime_confidence           double precision,
    top_down_context            text,
    alignment                   varchar,
    dominant_signal             varchar,
    recommendation              varchar,                                  -- Long-Aktion (BUY/BUY+/HOLD/SELL/NONE)
    confidence                  double precision,
    xai_explanation             text,
    price_at_analysis           double precision,
    top_down_anomaly_severity   varchar           DEFAULT 'none'::character varying,
    bottom_up_anomaly_severity  varchar           DEFAULT 'none'::character varying,
    indicators_snapshot         jsonb             DEFAULT '{}'::jsonb,
    short_action                text,                                     -- Short-Aktion (SHORT/SHORT+/HOLD/COVER/NONE); 2026-06-20 nachträglich ergänzt (steht daher physisch am Ende)
    risk_affinity               text,                                     -- Bond-Risikoaffinität (konservativ/neutral/risikofreudig); 2026-06-21 nachträglich ergänzt (steht daher physisch am Ende)
    short_xai                   text,                                     -- Erklärbare Short-Begründung (XAI), symmetrisch zu xai_explanation; 2026-06-22 nachträglich ergänzt (steht daher physisch am Ende)
    CONSTRAINT analysis_memory_pkey PRIMARY KEY (id)
);


-- ── backtester_reports ──────────────────────────────────────────────────────
-- Eine Zeile je Backtester-Report.
CREATE TABLE IF NOT EXISTS backtester_reports (
    id                       uuid              NOT NULL DEFAULT gen_random_uuid(),
    timestamp                timestamptz       NOT NULL DEFAULT now(),
    backtester_type          varchar           NOT NULL,
    ticker                   varchar,
    original_recommendation  varchar,
    price_at_recommendation  double precision,
    price_today              double precision,
    return_pct               double precision,
    verdict                  varchar,
    accuracy_30d             double precision,
    accuracy_60d             double precision,
    accuracy_90d             double precision,
    notes                    text,
    CONSTRAINT backtester_reports_pkey PRIMARY KEY (id)
);


-- ── portfolio_snapshots ─────────────────────────────────────────────────────
-- Eine Zeile je Portfolio-Monitor-Lauf.
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id                uuid              NOT NULL DEFAULT gen_random_uuid(),
    timestamp         timestamptz       NOT NULL DEFAULT now(),
    total_positions   integer,
    total_value_usd   double precision,
    cluster_risks     jsonb             DEFAULT '[]'::jsonb,
    alerts            jsonb             DEFAULT '[]'::jsonb,
    overall_health    varchar,
    metrics           jsonb             DEFAULT '{}'::jsonb,       -- Risiko-Kennzahlen (net_beta, Vola, Exposure …); 2026-06-20 nachträglich ergänzt (PR #11)
    CONSTRAINT portfolio_snapshots_pkey PRIMARY KEY (id)
);


-- ── conflicts ───────────────────────────────────────────────────────────────
-- Offene und erledigte Positions-Konflikte, die eine Nutzer-Entscheidung erfordern.
-- Ein Konflikt entsteht, wenn die Analyse-Empfehlung der gehaltenen Position widerspricht.
-- Lebenszyklus: status='open' → Nutzer entscheidet → status='resolved' + user_decision gesetzt.
CREATE TABLE IF NOT EXISTS conflicts (
    id            bigserial     PRIMARY KEY,
    ticker        text          NOT NULL,
    direction     text          NOT NULL,                   -- "long" | "short"
    verdict       text          NOT NULL,                   -- "HOLD" | "EXIT" | "REVERSE"
    reason        text,
    status        text          NOT NULL DEFAULT 'open',    -- "open" | "resolved"
    source        text          NOT NULL DEFAULT 'on_demand',  -- "on_demand" | "proactive"
    user_decision text,                                     -- "held" | "closed" | NULL
    created_at    timestamptz   DEFAULT now(),
    resolved_at   timestamptz
);


-- =============================================================================
-- Migrationshistorie (manuell gepflegt, bis ein echtes Migrations-Tool existiert)
-- =============================================================================
-- 2026-06-20  analysis_memory: Spalte short_action ergänzt (PR #9 / Block 3a F1-Nachbesserung).
--             ALTER TABLE analysis_memory ADD COLUMN IF NOT EXISTS short_action text;
-- 2026-06-20  portfolio_snapshots: Spalte metrics ergänzt (PR #11 / F4a-Review — Risiko-Kennzahlen).
--             ALTER TABLE portfolio_snapshots ADD COLUMN IF NOT EXISTS metrics jsonb DEFAULT '{}'::jsonb;
-- 2026-06-21  analysis_memory: Spalte risk_affinity ergänzt (feat/bond-risikoaffinitaet — Bond-Recompute-Bausteine).
--             ALTER TABLE analysis_memory ADD COLUMN IF NOT EXISTS risk_affinity text;
-- 2026-06-22  analysis_memory: Spalte short_xai ergänzt (feat/short-thesis-agent — erklärbare Short-Begründung, symmetrisch zu xai_explanation).
--             ALTER TABLE analysis_memory ADD COLUMN IF NOT EXISTS short_xai text;
-- ⚠️ DEPLOY: vor Merge einmalig auf Supabase ausführen:
--             ALTER TABLE analysis_memory ADD COLUMN IF NOT EXISTS risk_affinity text;
--             ALTER TABLE analysis_memory ADD COLUMN IF NOT EXISTS short_xai text;
-- 2026-06-22  conflicts: neue Tabelle für Konflikt-UX (feat/konflikt-ux — Task 3).
--             CREATE TABLE IF NOT EXISTS conflicts ( … ) — siehe oben.
