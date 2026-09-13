CREATE TABLE IF NOT EXISTS raw_news (
	id             SERIAL PRIMARY KEY,

	-- Идентификация и дедупликация
	guid           TEXT,
	url            TEXT NOT NULL UNIQUE,

	-- Временные метки
	timestamp_utc  TIMESTAMP NOT NULL,
	updated_at_utc TIMESTAMP,

	-- Источник
	source         VARCHAR(100) NOT NULL,
	origin_source  TEXT,
	origin_url     TEXT,

	-- Авторство и содержание
	authors        TEXT[],
	title          TEXT NOT NULL,
	image_url      TEXT,
	categories     TEXT[],
	description    TEXT,
	content        TEXT NOT NULL,

	-- Поля для LLM-пайплайна
	processed      BOOLEAN DEFAULT FALSE,
	processed_at   TIMESTAMP,
	llm_result     JSONB,

	created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Частичный индекс для мгновенной выборки необработанных новостей в LLM
CREATE INDEX IF NOT EXISTS idx_raw_news_unprocessed
	ON raw_news (timestamp_utc DESC) WHERE processed = FALSE;
