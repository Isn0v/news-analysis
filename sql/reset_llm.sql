-- Сброс результатов инференса LLM для повторной разметки
UPDATE raw_news 
SET 
    processed = FALSE, 
    processed_at = NULL, 
    llm_result = NULL;

-- Очистка результатов эвалуации
TRUNCATE TABLE news_market_impact;
