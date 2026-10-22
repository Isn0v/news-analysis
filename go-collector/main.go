package main

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/Isn0v/news/collector/config"
	"github.com/Isn0v/news/collector/database"
	"github.com/Isn0v/news/collector/model"
	"github.com/Isn0v/news/collector/parser"
	"github.com/Isn0v/news/collector/sources"
)

const (
	channelSize = 500
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("[Collector] Ошибка конфигурации: %v", err)
	}

	db := database.InitDB(cfg)
	defer db.Close()

	repo := database.NewRepository(db)

	// Настройка перехвата сигналов ОС для плавного завершения (Graceful Shutdown)
	stopChan := make(chan os.Signal, 1)
	signal.Notify(stopChan, os.Interrupt, syscall.SIGTERM)

	activeSources := sources.GetSources(cfg.Market)
	fmt.Printf("[Collector] Сервис запущен. Рынок: %s | Источников: %d | Периодичность опроса: %v\n", cfg.Market, len(activeSources), cfg.PollInterval)

	// Первый запуск сбора сразу при старте приложения
	runCollection(repo, activeSources)

	// Периодический запуск по таймеру
	ticker := time.NewTicker(cfg.PollInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			runCollection(repo, activeSources)
		case sig := <-stopChan:
			fmt.Printf("\n[Collector] Получен сигнал %v. Завершение работы...\n", sig)
			return
		}
	}
}

// runCollection запускает один цикл параллельного сбора новостей со всех активных источников.
func runCollection(repo *database.Repository, activeSources []model.Source) {
	fmt.Printf("\n[Collector] === Запуск цикла сбора (%s) [Источников: %d] ===\n", time.Now().UTC().Format(time.RFC3339), len(activeSources))

	ch := make(chan model.NewsItem, channelSize)
	var wg sync.WaitGroup

	// Конкурентный запуск воркеров на каждый источник
	for _, src := range activeSources {
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
