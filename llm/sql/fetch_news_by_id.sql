SELECT id, market, title, content, description, source, categories
FROM raw_news
WHERE id = %s;
