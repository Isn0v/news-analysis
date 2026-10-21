-- ==============================================================================
-- Полная DDL-схема Sentix для таблицы raw_news, news_market_impact и индексов
-- ==============================================================================

CREATE TABLE IF NOT EXISTS raw_news (
	id                  SERIAL PRIMARY KEY,

	-- Идентификация и дедупликация
	guid                TEXT,
	url                 TEXT NOT NULL UNIQUE,

	-- Временные метки
	timestamp_utc       TIMESTAMP NOT NULL,
	updated_at_utc      TIMESTAMP,

	-- Источник
	source              VARCHAR(100) NOT NULL,
	origin_source       TEXT,
	origin_url          TEXT,

	-- Авторство и содержание
	authors             TEXT[],
	title               TEXT NOT NULL,
	image_url           TEXT,
	categories          TEXT[],
	description         TEXT,
	content             TEXT NOT NULL,

	-- Поля для LLM-пайплайна
	processed           BOOLEAN DEFAULT FALSE,
	processed_at        TIMESTAMP,
	llm_result          JSONB,

	-- Поля для Market Evaluator пайплайна
	market_evaluated    BOOLEAN DEFAULT FALSE,
	market_evaluated_at TIMESTAMPTZ,

	-- Поля распределенной очереди воркеров
	locked_until        TIMESTAMPTZ,
	locked_by           VARCHAR(100),

	created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Идемпотентное добавление колонок на случай обновления существующей таблицы
ALTER TABLE raw_news ADD COLUMN IF NOT EXISTS market_evaluated BOOLEAN DEFAULT FALSE;
ALTER TABLE raw_news ADD COLUMN IF NOT EXISTS market_evaluated_at TIMESTAMPTZ;
ALTER TABLE raw_news ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;
ALTER TABLE raw_news ADD COLUMN IF NOT EXISTS locked_by VARCHAR(100);

-- Индексы очереди и выборок
CREATE INDEX IF NOT EXISTS idx_raw_news_unprocessed
	ON raw_news (timestamp_utc DESC) WHERE processed = FALSE;

CREATE INDEX IF NOT EXISTS idx_raw_news_market_unevaluated
	ON raw_news (timestamp_utc DESC) WHERE processed = TRUE AND market_evaluated = FALSE;

CREATE INDEX IF NOT EXISTS idx_raw_news_queue
	ON raw_news (timestamp_utc ASC) WHERE processed = FALSE;


-- Таблица квантитативной оценки рыночного влияния
CREATE TABLE IF NOT EXISTS news_market_impact (
	id                          BIGSERIAL PRIMARY KEY,
	news_id                     BIGINT NOT NULL REFERENCES raw_news(id) ON DELETE CASCADE,
	ticker                      VARCHAR(20) NOT NULL,
	symbol                      VARCHAR(20) NOT NULL,
	t0_timestamp                TIMESTAMPTZ NOT NULL,
	p0_price                    NUMERIC NOT NULL,
	pre_drift_pct               NUMERIC,
	volume_surge_ratio          NUMERIC,
	return_15m_pct              NUMERIC,
	return_1h_pct               NUMERIC,
	return_2h_pct               NUMERIC,
	return_4h_pct               NUMERIC,
	return_8h_pct               NUMERIC,
	return_24h_pct              NUMERIC,
	max_runup_pct               NUMERIC,
	max_drawdown_pct            NUMERIC,
	volatility_range_pct        NUMERIC,
	sentiment_label             VARCHAR(20),
	sentiment_score             NUMERIC,
	impact_magnitude            INT,
	target_horizon_hours        INT,
	is_mean_reverting_expected  BOOLEAN,
	is_impulse_confirmed        BOOLEAN,
	is_target_horizon_aligned   BOOLEAN,
	is_speculative              BOOLEAN DEFAULT FALSE,
	is_aligned_15m              BOOLEAN,
	is_aligned_1h               BOOLEAN,
	is_aligned_4h               BOOLEAN,
	is_aligned_24h              BOOLEAN,
	metrics_detail              JSONB,
	evaluated_at                TIMESTAMPTZ DEFAULT NOW(),
	CONSTRAINT uq_news_ticker UNIQUE (news_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_market_impact_news_id ON news_market_impact(news_id);
CREATE INDEX IF NOT EXISTS idx_market_impact_ticker ON news_market_impact(ticker);
CREATE INDEX IF NOT EXISTS idx_market_impact_t0 ON news_market_impact(t0_timestamp DESC);

-- Таблица версионирования миграций
CREATE TABLE IF NOT EXISTS schema_migrations (
	version     VARCHAR(255) PRIMARY KEY,
	applied_at  TIMESTAMPTZ DEFAULT NOW()
);
