-- Фильтрация статей по тегу/категории из массива categories
SELECT id, source, title, categories, timestamp_utc
FROM raw_news
WHERE categories @> ARRAY['DeFi']
ORDER BY timestamp_utc DESC;
