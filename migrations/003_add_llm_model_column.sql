-- ====================================================================
-- Миграция 003: Добавление колонки llm_model в raw_news и news_market_impact
-- ====================================================================

ALTER TABLE raw_news ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100);
CREATE INDEX IF NOT EXISTS idx_raw_news_llm_model ON raw_news (llm_model);

ALTER TABLE news_market_impact ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100);
CREATE INDEX IF NOT EXISTS idx_market_impact_llm_model ON news_market_impact (llm_model);

-- Заполняем модель для новостей, обработанных сегодня через ProxyAPI deepseek-chat
UPDATE raw_news
SET llm_model = 'deepseek/deepseek-chat'
WHERE processed = TRUE AND llm_model IS NULL AND processed_at >= '2026-10-22 00:00:00+00';

-- Для более ранних новостей, обрабатывавшихся локальным MLX
UPDATE raw_news
SET llm_model = 'mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit'
WHERE processed = TRUE AND llm_model IS NULL;

-- Синхронизируем llm_model в news_market_impact
UPDATE news_market_impact nmi
SET llm_model = rn.llm_model
FROM raw_news rn
WHERE nmi.news_id = rn.id AND nmi.llm_model IS NULL;

INSERT INTO schema_migrations (version) VALUES ('003_add_llm_model_column.sql') ON CONFLICT (version) DO NOTHING;
