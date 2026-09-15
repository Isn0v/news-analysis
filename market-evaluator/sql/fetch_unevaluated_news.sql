SELECT 
    n.id AS news_id,
    n.source,
    n.title,
    n.timestamp_utc,
    n.llm_result
FROM raw_news n
WHERE n.processed = TRUE
  AND n.llm_result IS NOT NULL
  AND COALESCE((n.llm_result->>'is_speculative')::boolean, false) = FALSE
  AND (
      jsonb_array_length(COALESCE(n.llm_result->'affected_assets', '[]'::jsonb)) > 0
      OR jsonb_array_length(COALESCE(n.llm_result->'detected_currencies', '[]'::jsonb)) > 0
  )
  AND NOT EXISTS (
      SELECT 1 
      FROM news_market_impact i 
      WHERE i.news_id = n.id
  )
ORDER BY n.timestamp_utc DESC
LIMIT %s;
