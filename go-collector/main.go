package main

import (
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/Isn0v/news/collector/database"
	"github.com/lib/pq"
	"github.com/mmcdole/gofeed"
)

// NewsItem — строгая схема для хранения сырых записей из RSS.
type NewsItem struct {
	GUID         string
	TimestampUTC string
	Source       string
	Authors      []string // все соавторы статьи
	Title        string
	URL          string
	ImageURL     string
	Categories   []string // теги и категории от редакции
	Description  string
	Content      string
}

// rssSource описывает один RSS-источник.
type rssSource struct {
	Name string
	URL  string
}

// sources — список всех RSS-лент. Добавь сюда новые источники по мере необходимости.
var sources = []rssSource{
	{Name: "the_defiant", URL: "https://thedefiant.io/feed/"},
	{Name: "coindesk", URL: "https://www.coindesk.com/arc/outboundfeeds/rss/"},
	// {Name: "cointelegraph", URL: "https://cointelegraph.com/rss"},
	// {Name: "decrypt",     URL: "https://decrypt.co/feed"},
}

// extractAuthors собирает всех авторов из item.
// Приоритет: dc:creator (поддерживает несколько), затем item.Authors, затем item.Author.
func extractAuthors(item *gofeed.Item) []string {
	// dc:creator — поддерживает несколько авторов (CoinDesk, Cointelegraph)
	if item.DublinCoreExt != nil && len(item.DublinCoreExt.Creator) > 0 {
		return item.DublinCoreExt.Creator
	}

	// item.Authors — стандартное поле Atom
	if len(item.Authors) > 0 {
		names := make([]string, 0, len(item.Authors))
		for _, a := range item.Authors {
			if a.Name != "" {
				names = append(names, a.Name)
			}
		}
		if len(names) > 0 {
			return names
		}
	}

	// Fallback на одиночный author
	if item.Author != nil && item.Author.Name != "" {
		return []string{item.Author.Name}
	}

	return nil
}

// extractImageURL извлекает URL обложки статьи.
// Проверяет media:content, item.Image и Enclosures.
func extractImageURL(item *gofeed.Item) string {
	// media:content (CoinDesk, The Defiant через media namespace)
	if mediaExt, ok := item.Extensions["media"]; ok {
		if contentList, ok := mediaExt["content"]; ok && len(contentList) > 0 {
			if url, ok := contentList[0].Attrs["url"]; ok && url != "" {
				return url
			}
		}
		// media:thumbnail (The Defiant)
		if thumbList, ok := mediaExt["thumbnail"]; ok && len(thumbList) > 0 {
			if url, ok := thumbList[0].Attrs["url"]; ok && url != "" {
				return url
			}
		}
	}

	// item.Image (стандартное поле RSS)
	if item.Image != nil && item.Image.URL != "" {
		return item.Image.URL
	}

	// Enclosures (часто используется для медиафайлов)
	for _, enc := range item.Enclosures {
		if strings.HasPrefix(enc.Type, "image/") {
			return enc.URL
		}
	}

	return ""
}

// fetchRSS парсит RSS-ленту и отправляет новости в канал.
func fetchRSS(src rssSource, ch chan<- NewsItem, wg *sync.WaitGroup) {
	defer wg.Done()

	fp := gofeed.NewParser()
	feed, err := fp.ParseURL(src.URL)
	if err != nil {
		log.Printf("[%s] Ошибка парсинга RSS: %v\n", src.Name, err)
		return
	}

	count := 0
	for _, item := range feed.Items {
		// Полный текст — из content:encoded, если есть; иначе fallback на description
		content := item.Content
		if strings.TrimSpace(content) == "" {
			content = item.Description
		}

		// Время публикации
		publishedAt := time.Now().UTC()
		if item.PublishedParsed != nil {
			publishedAt = item.PublishedParsed.UTC()
		}

		ch <- NewsItem{
			GUID:         item.GUID,
			TimestampUTC: publishedAt.Format(time.RFC3339),
			Source:       src.Name,
			Authors:      extractAuthors(item),
			Title:        item.Title,
			URL:          item.Link,
			ImageURL:     extractImageURL(item),
			Categories:   item.Categories,
			Description:  item.Description,
			Content:      content,
		}
		count++
	}
	fmt.Printf("[%s] Получено %d записей\n", src.Name, count)
}

func main() {
	db := database.InitDB()
	defer db.Close()

	// INSERT ... ON CONFLICT DO NOTHING — дедупликация по уникальному url.
	// pq.Array() используется для сохранения []string как PostgreSQL TEXT[].
	insertQuery := `
		INSERT INTO raw_news
			(guid, timestamp_utc, source, authors, title, url, image_url, categories, description, content)
		VALUES
			($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		ON CONFLICT (url) DO NOTHING`

	// Функция одного цикла сбора
	runCollection := func() {
		fmt.Println("[Collector] Запуск цикла сбора...")

		ch := make(chan NewsItem, 100)
		var wg sync.WaitGroup

		for _, src := range sources {
			wg.Add(1)
			go fetchRSS(src, ch, &wg)
		}

		// Закрываем канал, когда все горутины завершат работу
		go func() {
			wg.Wait()
			close(ch)
		}()

		saved, skipped := 0, 0
		for item := range ch {
			result, err := db.Exec(insertQuery,
				item.GUID,
				item.TimestampUTC,
				item.Source,
				pq.Array(item.Authors),     // []string → TEXT[]
				item.Title,
				item.URL,
				item.ImageURL,
				pq.Array(item.Categories), // []string → TEXT[]
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
				skipped++ // Новость уже была в базе
			}
		}
		fmt.Printf("[Collector] Цикл завершён: сохранено %d, пропущено (дубли) %d\n", saved, skipped)
	}

	// Первый запуск немедленно
	runCollection()

	// Опрос источников каждые 5 минут
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		runCollection()
	}
}
