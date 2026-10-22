package sources

import "github.com/Isn0v/news/collector/model"

// MoexSources — ведущие российские деловые и финансовые источники для анализа рынка акций и фьючерсов Мосбиржи (MOEX).
var MoexSources = []model.Source{
	// Эшелон 1: Деловые медиа с глубоким охватом макроэкономики и компаний РФ
	{Name: "rbc", URL: "https://rssexport.rbc.ru/rbcnews/news/30/full.rss", Market: "moex"}, // РБК Главные новости и экономика (полный текст)
	{Name: "bcs_express", URL: "https://bcs-express.ru/rss", Market: "moex"},                 // БКС Экспресс — ведущий брокерский анализ акций и дивидендов
	{Name: "finam", URL: "https://www.finam.ru/analysis/conews/rsspoint/", Market: "moex"}, // Финам — оперативные корпоративные новости компаний РФ

	// Эшелон 2: Информационные агентства (первоисточники регуляторики и макростатистики)
	{Name: "prime", URL: "https://1prime.ru/export/rss2/index.xml", Market: "moex"},   // Агентство ПРАЙМ — сводки ЦБ РФ, Минфина и корпоративные отчеты
	{Name: "interfax", URL: "https://www.interfax.ru/rss", Market: "moex"},             // Интерфакс — официальные корпоративные раскрытия и заявления
	{Name: "tass", URL: "https://tass.ru/rss/v2.xml", Market: "moex"},                 // ТАСС — официальная лента новостей РФ

	// Эшелон 3: Сообщество частных инвесторов и трейдеров Мосбиржи
	{Name: "smartlab", URL: "https://smart-lab.ru/rss/", Market: "moex"}, // Смартлаб — пульс розничных трейдеров РФ
}

// CryptoSources — проверенные и авторитетные источники криптовалютного рынка.
var CryptoSources = []model.Source{
	// Эшелон 1: Независимые расследования и глубокий ресерч
	{Name: "protos", URL: "https://protos.com/feed/", Market: "crypto"},                         // Журналистские расследования (~9 100 chars)
	{Name: "unchained", URL: "https://unchainedcrypto.com/feed/", Market: "crypto"},             // Журналистика Лоры Шин (~7 800 chars)
	{Name: "bitcoin_magazine", URL: "https://bitcoinmagazine.com/feed", Market: "crypto"},       // Старейшее Биткоин-издание (~4 000 chars)
	{Name: "smartliquidity", URL: "https://smartliquidity.info/feed/", Market: "crypto"},        // Аудит безопасности DeFi и смарт-контрактов (~19 100 chars)

	// Эшелон 2: Крупные отраслевые СМИ с сильным фактчекингом
	{Name: "beincrypto", URL: "https://beincrypto.com/feed/", Market: "crypto"},                 // Качественная аналитика и новости (~14 100 chars)
	{Name: "cryptoslate", URL: "https://cryptoslate.com/feed/", Market: "crypto"},               // Аналитика данных и рынка (~7 000 chars)
	{Name: "dailyhodl", URL: "https://dailyhodl.com/feed/", Market: "crypto"},                   // Авторитетный агрегатор новостей (~5 300 chars)
	{Name: "blockonomi", URL: "https://blockonomi.com/feed/", Market: "crypto"},                 // Аналитика рынка с TLDR (~7 400 chars)
	{Name: "finbold", URL: "https://finbold.com/feed/", Market: "crypto"},                       // Финансы, макроэкономика и регуляторика (~5 000 chars)
	{Name: "coinspeaker", URL: "https://www.coinspeaker.com/news/feed/", Market: "crypto"},       // Новости финтеха и Web3 (~7 900 chars)

	// Эшелон 3: Устоявшиеся новостные порталы и теханализ
	{Name: "bitcoinist", URL: "https://bitcoinist.com/feed/", Market: "crypto"},                 // Новости и ончейн (~5 800 chars)
	{Name: "newsbtc", URL: "https://newsbtc.com/feed/", Market: "crypto"},                       // Теханализ и новости (~4 500 chars)
	{Name: "coinjournal", URL: "https://coinjournal.net/feed/", Market: "crypto"},               // Обзоры рынка и ключевые тезисы (~5 500 chars)
	{Name: "zycrypto", URL: "https://zycrypto.com/feed/", Market: "crypto"},                     // Новости с тегами монет (~5 400 chars)
	{Name: "bitcoinworld", URL: "https://bitcoinworld.co.in/feed/", Market: "crypto"},           // Международные новости биткоина (~10 800 chars)
	{Name: "nulltx", URL: "https://nulltx.com/feed/", Market: "crypto"},                         // Обзоры технологий (~9 700 chars)

	// Эшелон 4: Авторская макро-аналитика / Substack
	{Name: "arthur_hayes", URL: "https://cryptohayes.substack.com/feed", Market: "crypto"},     // Эссе экс-главы BitMEX (~72 600 chars)
	{Name: "cobie", URL: "https://cobie.substack.com/feed", Market: "crypto"},                   // Философия рынка и эссе крипто-кита (~87 000 chars)
}

// Active по умолчанию настроен на источники Мосбиржи (РФ).
var Active = MoexSources

// GetSources возвращает список источников в зависимости от выбранного рынка ("moex", "crypto", "all").
func GetSources(market string) []model.Source {
	switch market {
	case "crypto":
		return CryptoSources
	case "all":
		res := make([]model.Source, 0, len(MoexSources)+len(CryptoSources))
		res = append(res, MoexSources...)
		res = append(res, CryptoSources...)
		return res
	case "moex":
		fallthrough
	default:
		return MoexSources
	}
}
