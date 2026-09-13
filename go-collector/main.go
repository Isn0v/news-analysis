package main

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/Isn0v/news/collector/database"
	"github.com/Isn0v/news/collector/model"
	"github.com/Isn0v/news/collector/parser"
	"github.com/Isn0v/news/collector/sources"
)

const (
	pollInterval = 5 * time.Minute
	channelSize  = 500
)

func main() {
	db := database.InitDB()
	defer db.Close()

	repo := database.NewRepository(db)

	// Настройка перехвата сигналов ОС для плавного завершения (Graceful Shutdown)
	stopChan := make(chan os.Signal, 1)
	signal.Notify(stopChan, os.Interrupt, syscall.SIGTERM)

	// Первый запуск сбора сразу при старте приложения
	runCollection(repo)

	// Периодический запуск по таймеру
	ticker := time.NewTicker(pollInterval)
	defer ticker.Stop()

	fmt.Printf("[Collector] Сервис запущен. Периодичность опроса: %v\n", pollInterval)

	for {
		select {
		case <-ticker.C:
			runCollection(repo)
		case sig := <-stopChan:
			fmt.Printf("\n[Collector] Получен сигнал %v. Завершение работы...\n", sig)
			return
		}
	}
}

// runCollection запускает один цикл параллельного сбора новостей со всех активных источников.
func runCollection(repo *database.Repository) {
	fmt.Printf("\n[Collector] === Запуск цикла сбора (%s) ===\n", time.Now().UTC().Format(time.RFC3339))

	ch := make(chan model.NewsItem, channelSize)
	var wg sync.WaitGroup

	// Конкурентный запуск воркеров на каждый источник
	for _, src := range sources.Active {
		wg.Add(1)
		go parser.FetchFeed(src, ch, &wg)
	}

	// Закрываем канал, когда все горутины закончат парсинг
	go func() {
		wg.Wait()
		close(ch)
	}()

	// Читаем из канала и сохраняем в базу через репозиторий
	saved, skipped, errors := 0, 0, 0
	for item := range ch {
		isNew, err := repo.Save(item)
		if err != nil {
			log.Printf("[DB] Ошибка сохранения '%s' [%s]: %v\n", item.Title, item.Source, err)
			errors++
			continue
		}

		if isNew {
			saved++
			fmt.Printf("[DB] Сохранено: [%s] %s\n", item.Source, item.Title)
		} else {
			skipped++
		}
	}

	fmt.Printf("[Collector] === Цикл завершён: сохранено %d, пропущено (дубли) %d, ошибок %d ===\n\n",
		saved, skipped, errors)
}
