package main

import (
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/Isn0v/news/collector/database"
)

// Строгая схема для хранения сырых записей[cite: 1]
type NewsItem struct {
	TimestampUTC string `json:"timestamp_utc"`
	Source       string `json:"source"`
	Title        string `json:"title"`
	Content      string `json:"content"`
}

// Пример функции опроса бесплатного эндпоинта DefiLlama[cite: 1, 2]
func fetchDefiLlama(ch chan<- NewsItem, wg *sync.WaitGroup) {
	defer wg.Done()

	// В рабочей версии здесь будет HTTP-запрос к https://api.llama.fi/hacks
	// Для примера симулируем задержку сети:
	time.Sleep(1 * time.Second)

	ch <- NewsItem{
		TimestampUTC: time.Now().UTC().Format(time.RFC3339),
		Source:       "defillama_hacks",
		Title:        "Взлом протокола X",
		Content:      "Ущерб составил $5M...",
	}
	fmt.Println("[Go] Успешно получены данные с DefiLlama")
}

func main() {

	db := database.InitDB()
	defer db.Close()

	newsChannel := make(chan NewsItem, 50)
	var wg sync.WaitGroup

	fmt.Println("Запуск конкурентного сбора данных...")

	// Запускаем горутины для каждого источника
	wg.Add(1)
	go fetchDefiLlama(newsChannel, &wg)

	// По аналогии сюда добавляются горутины для RSS SEC, CoinDesk, CryptoPanic[cite: 2]

	// Закрываем канал, когда все горутины завершат работу
	go func() {
		wg.Wait()
		close(newsChannel)
	}()

	// Подготовка SQL-запроса для вставки
	insertQuery := `INSERT INTO raw_news (timestamp_utc, source, title, content) VALUES ($1, $2, $3, $4)`

	for item := range newsChannel {
		_, err := db.Exec(insertQuery, item.TimestampUTC, item.Source, item.Title, item.Content)
		if err != nil {
			log.Printf("Ошибка сохранения записи (%s): %v\n", item.Title, err)
		} else {
			fmt.Printf("Сохранено в БД: [%s] %s\n", item.Source, item.Title)
		}
	}
}
