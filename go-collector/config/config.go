package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

// Config содержит параметры конфигурации сервиса сбора новостей.
type Config struct {
	PostgresHost     string
	PostgresPort     string
	PostgresUser     string
	PostgresPassword string
	PostgresDB       string
	PollInterval     time.Duration
}

// Load загружает переменные среды (с поддержкой локальных .env и ../.env файлов).
func Load() (*Config, error) {
	loadEnvFiles(".env", "../.env")

	cfg := &Config{
		PostgresHost:     getEnv("POSTGRES_HOST", "localhost"),
		PostgresPort:     getEnv("POSTGRES_PORT", "5432"),
		PostgresUser:     getEnv("POSTGRES_USER", "trader"),
		PostgresPassword: os.Getenv("POSTGRES_PASSWORD"),
		PostgresDB:       getEnv("POSTGRES_DB", "crypto_news"),
		PollInterval:     5 * time.Minute,
	}

	if cfg.PostgresPassword == "" {
		return nil, fmt.Errorf("переменная POSTGRES_PASSWORD не задана! Укажите пароль в файле .env или через переменную окружения")
	}

	if s := os.Getenv("COLLECTOR_POLL_INTERVAL_SECONDS"); s != "" {
		if sec, err := strconv.Atoi(s); err == nil && sec > 0 {
			cfg.PollInterval = time.Duration(sec) * time.Second
		}
	}

	return cfg, nil
}

// loadEnvFiles построчно считывает .env файлы без внешних зависимостей.
func loadEnvFiles(files ...string) {
	for _, file := range files {
		data, err := os.ReadFile(file)
		if err != nil {
			continue
		}
		for _, line := range strings.Split(string(data), "\n") {
			line = strings.TrimSpace(line)
			if line == "" || strings.HasPrefix(line, "#") {
				continue
			}
			parts := strings.SplitN(line, "=", 2)
			if len(parts) != 2 {
				continue
			}
			key := strings.TrimSpace(parts[0])
			val := strings.TrimSpace(parts[1])
			val = strings.Trim(val, `"'`)
			if os.Getenv(key) == "" {
				os.Setenv(key, val)
			}
		}
	}
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}
