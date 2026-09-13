package sources

import "github.com/Isn0v/news/collector/model"

// Active — проверенные и авторитетные источники без спама пресейлов и сомнительной рекламы.
// Все источники отдают 100% полный текст статьи (content:encoded).
var Active = []model.Source{
	// Эшелон 1: Независимые расследования и глубокий ресерч
	{Name: "protos",           URL: "https://protos.com/feed/"},              // Журналистские расследования (~9 100 chars)
	{Name: "unchained",        URL: "https://unchainedcrypto.com/feed/"},     // Журналистика Лоры Шин (~7 800 chars)
	{Name: "bitcoin_magazine", URL: "https://bitcoinmagazine.com/feed"},      // Старейшее Биткоин-издание (~4 000 chars)
	{Name: "smartliquidity",   URL: "https://smartliquidity.info/feed/"},     // Аудит безопасности DeFi и смарт-контрактов (~19 100 chars)

	// Эшелон 2: Крупные отраслевые СМИ с сильным фактчекингом
	{Name: "beincrypto",       URL: "https://beincrypto.com/feed/"},          // Качественная аналитика и новости (~14 100 chars)
	{Name: "cryptoslate",      URL: "https://cryptoslate.com/feed/"},         // Аналитика данных и рынка (~7 000 chars)
	{Name: "dailyhodl",        URL: "https://dailyhodl.com/feed/"},           // Авторитетный агрегатор новостей (~5 300 chars)
	{Name: "blockonomi",       URL: "https://blockonomi.com/feed/"},          // Аналитика рынка с TLDR (~7 400 chars)
	{Name: "finbold",          URL: "https://finbold.com/feed/"},             // Финансы, макроэкономика и регуляторика (~5 000 chars)
	{Name: "coinspeaker",      URL: "https://coinspeaker.com/feed/"},         // Новости финтеха и Web3 (~7 900 chars)

	// Эшелон 3: Устоявшиеся новостные порталы и теханализ
	{Name: "bitcoinist",       URL: "https://bitcoinist.com/feed/"},          // Новости и ончейн (~5 800 chars)
	{Name: "newsbtc",          URL: "https://www.newsbtc.com/feed/"},         // Теханализ и новости (~4 500 chars)
	{Name: "coinjournal",      URL: "https://coinjournal.net/feed/"},         // Обзоры рынка и ключевые тезисы (~5 500 chars)
	{Name: "zycrypto",         URL: "https://zycrypto.com/feed/"},            // Новости с тегами монет (~5 400 chars)
	{Name: "bitcoinworld",     URL: "https://bitcoinworld.co.in/feed/"},     // Международные новости биткоина (~10 800 chars)
	{Name: "nulltx",           URL: "https://nulltx.com/feed/"},              // Обзоры технологий (~9 700 chars)

	// Эшелон 4: Авторская макро-аналитика / Substack (топовые мыслители рынка)
	{Name: "arthur_hayes", URL: "https://cryptohayes.substack.com/feed"},     // Эссе экс-главы BitMEX (~72 600 chars)
	{Name: "cobie",        URL: "https://cobie.substack.com/feed"},            // Философия рынка и эссе крипто-кита (~87 000 chars)
}
