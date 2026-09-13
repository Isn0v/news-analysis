package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/Isn0v/news/collector/database"
	"github.com/lib/pq"
	"github.com/mmcdole/gofeed"
)

// NewsItem — полная схема данных, извлекаемых из RSS.
type NewsItem struct {
	GUID         string
	URL          string   // нормализованный URL без UTM-параметров
	TimestampUTC string   // дата публикации (pubDate)
	UpdatedAtUTC string   // дата редактирования (atom:updated), может быть пустой
	Source       string   // наш идентификатор источника ("coindesk")
	OriginSource string   // оригинальный издатель из <source> (Yahoo Finance)
	OriginURL    string   // URL оригинального издателя
	Authors      []string // все соавторы
	Title        string
	ImageURL     string
	Categories   []string
	Description  string
	Content      string
}

// rssSource описывает один RSS-источник.
type rssSource struct {
	Name string
	URL  string
}

// sources — список только тех RSS-лент, которые отдают 100% полный текст статьи (content:encoded).
// Урезанные источники (CoinDesk, The Defiant, Cointelegraph, Yahoo, Vitalik) исключены.
// Проверено live-запросами: минимум 4000 символов в content:encoded на первую статью.
var sources = []rssSource{
	// Проверенные крипто-медиа с полным текстом (проверено live)
	{Name: "bitcoin_magazine", URL: "https://bitcoinmagazine.com/feed"},      // ~4 000 chars
	{Name: "bitcoinist",       URL: "https://bitcoinist.com/feed/"},           // ~5 800 chars
	{Name: "cryptopotato",     URL: "https://cryptopotato.com/feed/"},        // ~7 900 chars
	{Name: "cryptonews",       URL: "https://cryptonews.com/news/feed/"},     // ~8 700 chars
	{Name: "cryptoslate",      URL: "https://cryptoslate.com/feed/"},         // ~7 000 chars
	{Name: "smartliquidity",   URL: "https://smartliquidity.info/feed/"},     // ~19 100 chars
	{Name: "cryptobreaking",   URL: "https://www.cryptobreaking.com/feed/"}, // ~7 700 chars
	{Name: "beincrypto",       URL: "https://beincrypto.com/feed/"},          // ~14 100 chars
	{Name: "newsbtc",          URL: "https://www.newsbtc.com/feed/"},         // ~4 500 chars
	{Name: "coinjournal",      URL: "https://coinjournal.net/feed/"},         // ~5 500 chars
	{Name: "finbold",          URL: "https://finbold.com/feed/"},             // ~5 000 chars

	// Авторская аналитика / Substack (полный текст подтверждён)
	{Name: "arthur_hayes", URL: "https://cryptohayes.substack.com/feed"}, // ~72 600 chars
	{Name: "cobie",        URL: "https://cobie.substack.com/feed"},        // ~87 000 chars
}

// stripUTM удаляет UTM-параметры из URL для надёжной дедупликации.
// Cointelegraph добавляет ?utm_source=rss_feed&utm_medium=rss в каждую ссылку.
func stripUTM(rawURL string) string {
	u, err := url.Parse(rawURL)
	if err != nil || rawURL == "" {
		return rawURL
	}
	q := u.Query()
	for key := range q {
		if strings.HasPrefix(key, "utm_") || key == "yptr" {
			q.Del(key)
		}
	}
	u.RawQuery = q.Encode()
	return u.String()
}

// extractAuthors собирает всех авторов статьи.
// Порядок приоритетов: dc:creator → item.Authors → item.Author.
// Для Cointelegraph чистит префикс "Cointelegraph by ".
func extractAuthors(item *gofeed.Item) []string {
	var names []string

	// dc:creator — поддерживает несколько авторов (CoinDesk, CryptoPotato, и др.)
	if item.DublinCoreExt != nil && len(item.DublinCoreExt.Creator) > 0 {
		for _, creator := range item.DublinCoreExt.Creator {
			// Cointelegraph: "Cointelegraph by John Doe" → "John Doe"
			name := strings.TrimPrefix(creator, "Cointelegraph by ")
			name = strings.TrimSpace(name)
			if name != "" {
				names = append(names, name)
			}
		}
		if len(names) > 0 {
			return names
		}
	}

	// item.Authors — Atom-стандарт
	if len(item.Authors) > 0 {
		for _, a := range item.Authors {
			if a.Name != "" {
				names = append(names, a.Name)
			}
		}
		if len(names) > 0 {
			return names
		}
	}

	// Fallback: одиночный автор
	if item.Author != nil && item.Author.Name != "" {
		return []string{item.Author.Name}
	}

	return nil
}

// extractImageURL извлекает URL обложки статьи из нескольких возможных мест.
// Порядок: media:content → media:thumbnail → item.Image → enclosures (только image/*).
func extractImageURL(item *gofeed.Item) string {
	if mediaExt, ok := item.Extensions["media"]; ok {
		// media:content
		if list, ok := mediaExt["content"]; ok && len(list) > 0 {
			if u := list[0].Attrs["url"]; u != "" {
				return u
			}
		}
		// media:thumbnail (The Defiant)
		if list, ok := mediaExt["thumbnail"]; ok && len(list) > 0 {
			if u := list[0].Attrs["url"]; u != "" {
				return u
			}
		}
	}

	// Стандартное поле RSS
	if item.Image != nil && item.Image.URL != "" {
		return item.Image.URL
	}

	// Enclosures (только изображения)
	for _, enc := range item.Enclosures {
		if strings.HasPrefix(enc.Type, "image/") {
			return enc.URL
		}
	}

	return ""
}

// extractUpdatedAt извлекает дату последнего редактирования из atom:updated.
// Уникален для Cointelegraph.
func extractUpdatedAt(item *gofeed.Item) string {
	if item.UpdatedParsed != nil {
		return item.UpdatedParsed.UTC().Format(time.RFC3339)
	}
	return ""
}

// extractOriginSource извлекает оригинального издателя из тега <source>.
// Используется в Yahoo Finance: <source url="https://pitchbook.com/">Pitchbook</source>
// gofeed кладёт его в item.Extensions[""]["source"]
func extractOriginSource(item *gofeed.Item) (name, srcURL string) {
	if item.Extensions == nil {
		return "", ""
	}
	// Стандартный (без namespace) тег <source> попадает в Extensions под ключом ""
	if ext, ok := item.Extensions[""]; ok {
		if sources, ok := ext["source"]; ok && len(sources) > 0 {
			s := sources[0]
			return strings.TrimSpace(s.Value), s.Attrs["url"]
		}
	}
	return "", ""
}

// fetchRSS парсит RSS-ленту источника и отправляет все статьи в канал.
func fetchRSS(src rssSource, ch chan<- NewsItem, wg *sync.WaitGroup) {
	defer wg.Done()

	fp := gofeed.NewParser()
	// Некоторые сайты блокируют запросы без User-Agent
	fp.UserAgent = "Mozilla/5.0 (compatible; news-analysis-bot/1.0)"

	feed, err := fp.ParseURL(src.URL)
	if err != nil {
		log.Printf("[%s] Ошибка парсинга RSS: %v\n", src.Name, err)
		return
	}

	count := 0
	for _, item := range feed.Items {
		// Полный текст — content:encoded если есть, иначе description
		content := strings.TrimSpace(item.Content)
		if content == "" {
			content = item.Description
		}

		// Время публикации
		publishedAt := time.Now().UTC()
		if item.PublishedParsed != nil {
			publishedAt = item.PublishedParsed.UTC()
		}

		// Нормализуем URL — убираем UTM-параметры
		cleanURL := stripUTM(item.Link)

		// Yahoo Finance: <source> tag хранит оригинальное издание
		originName, originURL := extractOriginSource(item)

		ch <- NewsItem{
			GUID:         item.GUID,
			URL:          cleanURL,
			TimestampUTC: publishedAt.Format(time.RFC3339),
			UpdatedAtUTC: extractUpdatedAt(item),
			Source:       src.Name,
			OriginSource: originName,
			OriginURL:    originURL,
			Authors:      extractAuthors(item),
			Title:        item.Title,
			ImageURL:     extractImageURL(item),
			Categories:   item.Categories,
			Description:  item.Description,
			Content:      content,
		}
		count++
	}
	fmt.Printf("[%s] Получено %d записей\n", src.Name, count)
}

// nullableString возвращает sql.NullString из строки (пустая → NULL в БД).
func nullableString(s string) sql.NullString {
	return sql.NullString{String: s, Valid: s != ""}
}

func main() {
	db := database.InitDB()
	defer db.Close()

	insertQuery := `
		INSERT INTO raw_news (
			guid, url, timestamp_utc, updated_at_utc,
			source, origin_source, origin_url,
			authors, title, image_url, categories,
			description, content
		) VALUES (
			$1, $2, $3, $4,
			$5, $6, $7,
			$8, $9, $10, $11,
			$12, $13
		)
		ON CONFLICT (url) DO NOTHING`

	runCollection := func() {
		fmt.Println("[Collector] Запуск цикла сбора...")

		ch := make(chan NewsItem, 200)
		var wg sync.WaitGroup

		for _, src := range sources {
			wg.Add(1)
			go fetchRSS(src, ch, &wg)
		}

		go func() {
			wg.Wait()
			close(ch)
		}()

		saved, skipped := 0, 0
		for item := range ch {
			result, err := db.Exec(insertQuery,
				nullableString(item.GUID),
				item.URL,
				item.TimestampUTC,
				nullableString(item.UpdatedAtUTC),
				item.Source,
				nullableString(item.OriginSource),
				nullableString(item.OriginURL),
				pq.Array(item.Authors),
				item.Title,
				nullableString(item.ImageURL),
				pq.Array(item.Categories),
				item.Description,
				item.Content,
			)
			if err != nil {
				log.Printf("[DB] Ошибка сохранения '%s': %v\n", item.Title, err)
				continue
			}
			rows, _ := result.RowsAffected()
			if rows > 0 {
				saved++
				fmt.Printf("[DB] Сохранено: [%s] %s\n", item.Source, item.Title)
			} else {
				skipped++
			}
		}
		fmt.Printf("[Collector] Цикл завершён: сохранено %d, пропущено (дубли) %d\n", saved, skipped)
	}

	// Первый запуск сразу при старте
	runCollection()

	// Опрос каждые 5 минут
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		runCollection()
	}
}
