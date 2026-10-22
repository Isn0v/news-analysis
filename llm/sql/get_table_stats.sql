SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE processed = TRUE) AS processed,
    COUNT(*) FILTER (WHERE processed = FALSE) AS unprocessed,
    COUNT(*) FILTER (WHERE market = 'crypto') AS crypto_total,
    COUNT(*) FILTER (WHERE market = 'crypto' AND processed = TRUE) AS crypto_processed,
    COUNT(*) FILTER (WHERE market = 'crypto' AND processed = FALSE) AS crypto_unprocessed,
    COUNT(*) FILTER (WHERE market = 'moex') AS moex_total,
    COUNT(*) FILTER (WHERE market = 'moex' AND processed = TRUE) AS moex_processed,
    COUNT(*) FILTER (WHERE market = 'moex' AND processed = FALSE) AS moex_unprocessed
FROM raw_news;
