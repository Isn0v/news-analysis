UPDATE raw_news
SET 
    processed = TRUE,
    processed_at = NOW(),
    llm_result = %s::jsonb
WHERE id = %s;
