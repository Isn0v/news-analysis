package parser

import (
	"fmt"
	"log"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/Isn0v/news/collector/model"
	"github.com/mmcdole/gofeed"
)

// StripUTM удаляет UTM-метки и трекинг-параметры из ссылок для корректной дедупликации.
func StripUTM(rawURL string) string {
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

// ExtractAuthors извлекает список авторов статьи с поддержкой нескольких соавторов
// и очисткой специфических префиксов (например, "Cointelegraph by ").
func ExtractAuthors(item *gofeed.Item) []string {
	var names []string

	if item.DublinCoreExt != nil && len(item.DublinCoreExt.Creator) > 0 {
		for _, creator := range item.DublinCoreExt.Creator {
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

	if item.Author != nil && item.Author.Name != "" {
		return []string{item.Author.Name}
	}

	return nil
}

// ExtractImageURL достаёт ссылку на обложку из media:content, media:thumbnail, item.Image или enclosures.
func ExtractImageURL(item *gofeed.Item) string {
	if mediaExt, ok := item.Extensions["media"]; ok {
		if list, ok := mediaExt["content"]; ok && len(list) > 0 {
			if u := list[0].Attrs["url"]; u != "" {
				return u
			}
		}
		if list, ok := mediaExt["thumbnail"]; ok && len(list) > 0 {
			if u := list[0].Attrs["url"]; u != "" {
				return u
			}
		}
	}

	if item.Image != nil && item.Image.URL != "" {
		return item.Image.URL
	}

	for _, enc := range item.Enclosures {
		if strings.HasPrefix(enc.Type, "image/") {
			return enc.URL
		}
	}

	return ""
}

// ExtractUpdatedAt возвращает дату редактирования из atom:updated в формате RFC3339.
func ExtractUpdatedAt(item *gofeed.Item) string {
	if item.UpdatedParsed != nil {
		return item.UpdatedParsed.UTC().Format(time.RFC3339)
	}
	return ""
}

// ExtractOriginSource читает оригинального издателя из тега <source url="...">.
func ExtractOriginSource(item *gofeed.Item) (name, srcURL string) {
	if item.Extensions == nil {
		return "", ""
	}
	if ext, ok := item.Extensions[""]; ok {
		if sourceTags, ok := ext["source"]; ok && len(sourceTags) > 0 {
			s := sourceTags[0]
			return strings.TrimSpace(s.Value), s.Attrs["url"]
		}
	}
	return "", ""
}

// FetchFeed скачивает и парсит RSS-ленту, отправляя готовые NewsItem в канал.
func FetchFeed(src model.Source, ch chan<- model.NewsItem, wg *sync.WaitGroup) {
	defer wg.Done()

	fp := gofeed.NewParser()
	fp.UserAgent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

	feed, err := fp.ParseURL(src.URL)
	if err != nil {
		log.Printf("[%s] Ошибка парсинга RSS: %v\n", src.Name, err)
		return
	}

	count := 0
	for _, item := range feed.Items {
		content := strings.TrimSpace(item.Content)
		if content == "" {
			content = item.Description
		}

		publishedAt := time.Now().UTC()
		if item.PublishedParsed != nil {
			publishedAt = item.PublishedParsed.UTC()
		}

		cleanURL := StripUTM(item.Link)
		originName, originURL := ExtractOriginSource(item)

		ch <- model.NewsItem{
			GUID:         item.GUID,
			URL:          cleanURL,
			TimestampUTC: publishedAt.Format(time.RFC3339),
			UpdatedAtUTC: ExtractUpdatedAt(item),
			Source:       src.Name,
			OriginSource: originName,
			OriginURL:    originURL,
			Authors:      ExtractAuthors(item),
			Title:        item.Title,
			ImageURL:     ExtractImageURL(item),
			Categories:   item.Categories,
			Description:  item.Description,
			Content:      content,
		}
		count++
	}
	fmt.Printf("[%s] Успешно получено: %d записей\n", src.Name, count)
}
