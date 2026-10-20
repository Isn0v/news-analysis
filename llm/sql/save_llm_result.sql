UPDATE raw_news
SET 
    processed = TRUE,
    processed_at = NOW(),
    llm_result = %s::jsonb,
    locked_until = NULL,
    locked_by = NULL
WHERE id = %s;
