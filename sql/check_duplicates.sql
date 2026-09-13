-- Проверка на наличие дубликатов по URL
SELECT url, COUNT(*) AS cnt
FROM raw_news
GROUP BY url
HAVING COUNT(*) > 1;
