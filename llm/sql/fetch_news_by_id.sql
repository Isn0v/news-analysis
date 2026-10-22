SELECT id, title, content, description, source, categories
FROM raw_news
WHERE id = %s;
