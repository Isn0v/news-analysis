package config

import (
	"os"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	// Временная установка переменной окружения для теста
	os.Setenv("POSTGRES_PASSWORD", "testpass")
	defer os.Unsetenv("POSTGRES_PASSWORD")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}

	if cfg.PostgresUser != "trader" {
		t.Errorf("expected user trader, got %s", cfg.PostgresUser)
	}
	if cfg.PostgresDB != "crypto_news" {
		t.Errorf("expected db crypto_news, got %s", cfg.PostgresDB)
	}
}
