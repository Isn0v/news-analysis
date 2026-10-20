-- ====================================================================
-- Миграция 002: Поля и индексы распределенной очереди для параллельных LLM-воркеров
-- ====================================================================

-- Поля блокировки задачи за конкретным воркером
ALTER TABLE raw_news ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;
ALTER TABLE raw_news ADD COLUMN IF NOT EXISTS locked_by VARCHAR(100);

-- Оптимизированный частичный индекс для мгновенного захвата задач воркерами по алгоритму FIFO
CREATE INDEX IF NOT EXISTS idx_raw_news_queue
    ON raw_news (timestamp_utc ASC)
    WHERE processed = FALSE;
