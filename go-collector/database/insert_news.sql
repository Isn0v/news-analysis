INSERT INTO raw_news (
	guid, url, timestamp_utc, updated_at_utc,
	source, origin_source, origin_url,
	authors, title, image_url, categories,
	description, content, market
) VALUES (
	$1, $2, $3, $4,
	$5, $6, $7,
	$8, $9, $10, $11,
	$12, $13, $14
)
ON CONFLICT (url) DO NOTHING;
