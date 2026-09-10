package main

import (
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/Isn0v/news/collector/database"
	"github.com/mmcdole/gofeed"
)

// NewsItem — строгая схема для хранения сырых записей из RSS.
type NewsItem struct {
	TimestampUTC string
	Source       string
	Author       string
	Title        string
	URL          string
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
	// {Name: "coindesk",    URL: "https://www.coindesk.com/arc/outboundfeeds/rss/"},
	// {Name: "cointelegraph", URL: "https://cointelegraph.com/rss"},
	// {Name: "decrypt",     URL: "https://decrypt.co/feed"},
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
		// Берём автора: сначала из item.Author, потом из item.DublinCoreExt
		author := ""
		if item.Author != nil {
			author = item.Author.Name
		}

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
			TimestampUTC: publishedAt.Format(time.RFC3339),
			Source:       src.Name,
			Author:       author,
			Title:        item.Title,
			URL:          item.Link,
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
	insertQuery := `
		INSERT INTO raw_news (timestamp_utc, source, author, title, url, description, content)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
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
				item.TimestampUTC, item.Source, item.Author,
				item.Title, item.URL, item.Description, item.Content)
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
