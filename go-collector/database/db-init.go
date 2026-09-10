package database

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/lib/pq"
)

// InitDB подключается к PostgreSQL и создаёт таблицу raw_news, если её нет.
// Колонка url имеет ограничение UNIQUE — это главный инструмент дедупликации.
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
		id           SERIAL PRIMARY KEY,
		timestamp_utc TIMESTAMP NOT NULL,
		source       VARCHAR(100) NOT NULL,
		author       TEXT,
		title        TEXT NOT NULL,
		url          TEXT NOT NULL UNIQUE,
		description  TEXT,
		content      TEXT NOT NULL,
		created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);`

	if _, err = db.Exec(createTableQuery); err != nil {
		log.Fatalf("Ошибка создания таблицы: %v", err)
	}

	fmt.Println("[DB] Успешное подключение к PostgreSQL")
	return db
}
