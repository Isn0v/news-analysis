-- Последние 10 статей с превью текста и метаданными
SELECT
    id,
    source,
    title,
    authors,
    categories,
    timestamp_utc,
    char_length(content) AS content_chars,
    LEFT(content, 300)   AS content_preview
FROM raw_news
ORDER BY timestamp_utc DESC
LIMIT 10;
