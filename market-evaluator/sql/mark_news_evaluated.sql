UPDATE raw_news
SET market_evaluated = TRUE,
    market_evaluated_at = NOW()
WHERE id = %s;
