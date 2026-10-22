package database

import (
	"fmt"
	"testing"
	"time"

	"github.com/Isn0v/news/collector/config"
	"github.com/Isn0v/news/collector/model"
)

func TestRepository_SaveAndDeduplicate(t *testing.T) {
	cfg, err := config.Load()
	if err != nil {
		t.Skipf("Config loading failed: %v", err)
	}

	db := InitDB(cfg)
	defer db.Close()

	if err := db.Ping(); err != nil {
		t.Skipf("PostgreSQL is not reachable: %v", err)
	}

	repo := NewRepository(db)

	uniqueURL := fmt.Sprintf("https://test.example.com/article-%d", time.Now().UnixNano())
	item := model.NewsItem{
		GUID:         "guid-test-1",
		URL:          uniqueURL,
		TimestampUTC: time.Now().UTC().Format(time.RFC3339),
		Source:       "TestFeed",
		Title:        "Integration Test News",
		Authors:      []string{"Tester"},
		Categories:   []string{"TestCat"},
		Description:  "Short test description",
		Content:      "Full test content for integration verification",
		Market:       "moex",
	}

	// 1. Первая вставка должна успешно сохраниться (isNew == true)
	isNew, err := repo.Save(item)
	if err != nil {
		t.Fatalf("First Save failed: %v", err)
	}
	if !isNew {
		t.Errorf("Expected isNew to be true on first insertion")
	}

	// 2. Вторая вставка той же новости должна быть проигнорирована по уникальному URL (isNew == false)
	isNewSecond, err := repo.Save(item)
	if err != nil {
		t.Fatalf("Second Save failed: %v", err)
	}
	if isNewSecond {
		t.Errorf("Expected isNew to be false on duplicate insertion")
	}

	// Очистка тестовых данных
	_, _ = db.Exec("DELETE FROM raw_news WHERE url = $1", uniqueURL)
}
