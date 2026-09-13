-- Статистика качества и полноты текстов по источникам
SELECT
    source,
    COUNT(*)                       AS articles,
    AVG(char_length(content))::INT AS avg_content_chars,
    MIN(char_length(content))      AS min_chars,
    MAX(char_length(content))      AS max_chars
FROM raw_news
GROUP BY source
ORDER BY avg_content_chars DESC;
