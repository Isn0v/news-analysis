-- Статьи, уже обработанные LLM с сохранённым результатом анализа
SELECT
    id,
    source,
    title,
    timestamp_utc,
    processed_at,
    llm_result
FROM raw_news
WHERE processed = TRUE
ORDER BY processed_at DESC;
