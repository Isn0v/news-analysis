WITH claim AS (
    SELECT id
    FROM raw_news
    WHERE processed = FALSE 
      AND (locked_until IS NULL OR locked_until < NOW())
    ORDER BY timestamp_utc ASC
    LIMIT %s
    FOR UPDATE SKIP LOCKED
)
UPDATE raw_news
SET locked_until = NOW() + (%s * INTERVAL '1 MINUTE'),
    locked_by = %s
FROM claim
WHERE raw_news.id = claim.id
RETURNING 
    raw_news.id, 
    raw_news.source, 
    raw_news.title, 
    COALESCE(raw_news.categories, '{}') AS categories, 
    COALESCE(raw_news.description, '') AS description, 
    COALESCE(raw_news.content, '') AS content, 
    raw_news.timestamp_utc;
