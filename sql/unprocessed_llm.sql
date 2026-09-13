-- Статьи, ожидающие обработки LLM (очередь для Python-сервиса)
SELECT id, source, title, timestamp_utc, char_length(content) AS content_chars
FROM raw_news
WHERE processed = FALSE
ORDER BY timestamp_utc DESC;
