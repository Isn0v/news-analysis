SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE processed = TRUE) AS processed,
    COUNT(*) FILTER (WHERE processed = FALSE) AS unprocessed
FROM raw_news;
