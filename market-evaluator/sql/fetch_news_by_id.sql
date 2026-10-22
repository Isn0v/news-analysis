SELECT id AS news_id, source, title, timestamp_utc, llm_result
FROM raw_news
WHERE id = %s;
