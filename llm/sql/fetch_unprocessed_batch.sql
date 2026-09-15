SELECT 
    id, 
    source, 
    title, 
    COALESCE(categories, '{}') AS categories, 
    COALESCE(description, '') AS description, 
    COALESCE(content, '') AS content, 
    timestamp_utc
FROM raw_news
WHERE processed = FALSE
ORDER BY timestamp_utc ASC
LIMIT %s;
