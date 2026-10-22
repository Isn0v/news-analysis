-- ====================================================================
-- Миграция 004: Добавление колонки market в raw_news и news_market_impact
-- Разделение рынков: 'crypto' (криптовалюты / Binance) vs 'moex' (Мосбиржа)
-- ====================================================================

-- 1. Добавляем колонку market в таблицу raw_news
ALTER TABLE raw_news ADD COLUMN IF NOT EXISTS market VARCHAR(50) NOT NULL DEFAULT 'crypto';
CREATE INDEX IF NOT EXISTS idx_raw_news_market ON raw_news (market);

-- 2. Добавляем колонку market в таблицу news_market_impact
ALTER TABLE news_market_impact ADD COLUMN IF NOT EXISTS market VARCHAR(50) NOT NULL DEFAULT 'crypto';
CREATE INDEX IF NOT EXISTS idx_market_impact_market ON news_market_impact (market);

-- 3. Гарантируем, что все существующие записи промаркированы как crypto
UPDATE raw_news SET market = 'crypto' WHERE market IS NULL OR market = '';
UPDATE news_market_impact SET market = 'crypto' WHERE market IS NULL OR market = '';

-- 4. Фиксация в реестре миграций
INSERT INTO schema_migrations (version) VALUES ('004_add_market_column.sql') ON CONFLICT (version) DO NOTHING;
