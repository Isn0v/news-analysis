-- Фильтрация статей конкретного автора из массива authors
SELECT id, source, title, authors, timestamp_utc
FROM raw_news
WHERE authors @> ARRAY['Arthur Hayes']
ORDER BY timestamp_utc DESC;
