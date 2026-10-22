package sources

import "github.com/Isn0v/news/collector/model"

// Active — ведущие российские деловые и финансовые источники для анализа рынка акций и фьючерсов Мосбиржи (MOEX).
var Active = []model.Source{
	// Эшелон 1: Деловые медиа с глубоким охватом макроэкономики и компаний РФ
	{Name: "rbc",         URL: "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",     Market: "moex"}, // РБК Главные новости и экономика (полный текст)
	{Name: "bcs_express", URL: "https://bcs-express.ru/rss",                            Market: "moex"}, // БКС Экспресс — ведущий брокерский анализ акций и дивидендов
	{Name: "finam",       URL: "https://www.finam.ru/analysis/conews/rsspoint/",        Market: "moex"}, // Финам — оперативные корпоративные новости компаний РФ

	// Эшелон 2: Информационные агентства (первоисточники регуляторики и макростатистики)
	{Name: "prime",       URL: "https://1prime.ru/export/rss2/index.xml",               Market: "moex"}, // Агентство ПРАЙМ — сводки ЦБ РФ, Минфина и корпоративные отчеты
	{Name: "interfax",    URL: "https://www.interfax.ru/rss",                           Market: "moex"}, // Интерфакс — официальные корпоративные раскрытия и заявления
	{Name: "tass",        URL: "https://tass.ru/rss/v2.xml",                            Market: "moex"}, // ТАСС — официальная лента новостей РФ

	// Эшелон 3: Сообщество частных инвесторов и трейдеров Мосбиржи
	{Name: "smartlab",    URL: "https://smart-lab.ru/rss/",                             Market: "moex"}, // Смартлаб — пульс розничных трейдеров РФ
}
