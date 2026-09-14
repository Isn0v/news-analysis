-- Общее количество всех собранных статей в базе данных
-- (включая разделение на обработанные и ожидающие анализа LLM)
SELECT
    COUNT(*)                                  AS total_articles,
    COUNT(*) FILTER (WHERE processed = TRUE)  AS processed_articles,
    COUNT(*) FILTER (WHERE processed = FALSE) AS unprocessed_articles
FROM raw_news;
