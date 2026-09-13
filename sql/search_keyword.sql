-- Поиск статей по ключевому слову в заголовке или тексте статьи
SELECT id, source, title, timestamp_utc
FROM raw_news
WHERE
    title   ILIKE '%bitcoin%'
 OR content ILIKE '%bitcoin%'
ORDER BY timestamp_utc DESC;
