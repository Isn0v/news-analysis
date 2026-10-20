UPDATE raw_news
SET 
    locked_until = NULL,
    locked_by = NULL
WHERE id = ANY(%s) 
  AND processed = FALSE;
