package sources

import "github.com/Isn0v/news/collector/model"

// Active — проверенные RSS-ленты, отдающие 100% полный текст статьи (content:encoded).
var Active = []model.Source{
	// Крипто-медиа с подтверждённым полным текстом
	{Name: "bitcoin_magazine", URL: "https://bitcoinmagazine.com/feed"},      // ~4 000 chars
	{Name: "bitcoinist",       URL: "https://bitcoinist.com/feed/"},          // ~5 800 chars
	{Name: "cryptopotato",     URL: "https://cryptopotato.com/feed/"},        // ~7 900 chars
	{Name: "cryptonews",       URL: "https://cryptonews.com/news/feed/"},     // ~8 700 chars
	{Name: "cryptoslate",      URL: "https://cryptoslate.com/feed/"},         // ~7 000 chars
	{Name: "smartliquidity",   URL: "https://smartliquidity.info/feed/"},     // ~19 100 chars
	{Name: "cryptobreaking",   URL: "https://www.cryptobreaking.com/feed/"}, // ~7 700 chars
	{Name: "beincrypto",       URL: "https://beincrypto.com/feed/"},          // ~14 100 chars
	{Name: "newsbtc",          URL: "https://www.newsbtc.com/feed/"},         // ~4 500 chars
	{Name: "coinjournal",      URL: "https://coinjournal.net/feed/"},         // ~5 500 chars
	{Name: "finbold",          URL: "https://finbold.com/feed/"},             // ~5 000 chars

	// Авторские лонгриды / Substack (глубокая аналитика)
	{Name: "arthur_hayes", URL: "https://cryptohayes.substack.com/feed"}, // ~72 600 chars
	{Name: "cobie",        URL: "https://cobie.substack.com/feed"},        // ~87 000 chars
}
