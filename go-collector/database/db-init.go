package database

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/lib/pq"
)

// InitDB подключается к PostgreSQL и создаёт таблицу raw_news, если её нет.
func InitDB() *sql.DB {
	host := os.Getenv("POSTGRES_HOST")
	port := os.Getenv("POSTGRES_PORT")
	user := os.Getenv("POSTGRES_USER")
	password := os.Getenv("POSTGRES_PASSWORD")
	dbname := os.Getenv("POSTGRES_DB")

	psqlInfo := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		host, port, user, password, dbname)

	db, err := sql.Open("postgres", psqlInfo)
	if err != nil {
		log.Fatalf("Ошибка подключения к БД: %v", err)
	}

	if err = db.Ping(); err != nil {
		log.Fatalf("База данных недоступна: %v", err)
	}

	createTableQuery := `
	CREATE TABLE IF NOT EXISTS raw_news (
		id             SERIAL PRIMARY KEY,

		-- Идентификация
		guid           TEXT,
		url            TEXT NOT NULL UNIQUE,   -- ключ дедупликации (без UTM-параметров)

		-- Временны́е метки
		timestamp_utc  TIMESTAMP NOT NULL,     -- дата публикации из pubDate
		updated_at_utc TIMESTAMP,              -- дата последнего редактирования (atom:updated, если есть)

		-- Источник
		source         VARCHAR(100) NOT NULL,  -- наш идентификатор источника (e.g. "coindesk")
		origin_source  TEXT,                   -- оригинальный издатель (Yahoo Finance: <source> tag)
		origin_url     TEXT,                   -- URL оригинального издателя

		-- Авторство
		authors        TEXT[],                 -- все соавторы ["Alice", "Bob"]

		-- Контент
		title          TEXT NOT NULL,
		image_url      TEXT,
		categories     TEXT[],                 -- теги и категории от редакции
		description    TEXT,                   -- краткий анонс (description)
		content        TEXT NOT NULL,          -- полный текст (content:encoded) или fallback на description

		-- Поля для LLM-пайплайна
		processed      BOOLEAN DEFAULT FALSE,
		processed_at   TIMESTAMP,
		llm_result     JSONB,                  -- {"sentiment": "bullish", "score": 8, "tickers": ["BTC"]}

		created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);

	-- Частичный индекс для быстрой выборки необработанных записей LLM-сервисом
	CREATE INDEX IF NOT EXISTS idx_raw_news_unprocessed
		ON raw_news (timestamp_utc DESC) WHERE processed = FALSE;`

	if _, err = db.Exec(createTableQuery); err != nil {
		log.Fatalf("Ошибка создания таблицы: %v", err)
	}

	fmt.Println("[DB] Успешное подключение к PostgreSQL")
	return db
}
