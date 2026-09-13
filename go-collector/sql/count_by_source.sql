-- Подсчёт количества сохранённых статей по каждому источнику
SELECT source, COUNT(*) AS total
FROM raw_news
GROUP BY source
ORDER BY total DESC;
