package database

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/lib/pq"
)

// Инициализация подключения к БД
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

	// Автоматическое создание таблицы по нашей схеме[cite: 1]
	createTableQuery := `
	CREATE TABLE IF NOT EXISTS raw_news (
		id SERIAL PRIMARY KEY,
		timestamp_utc TIMESTAMP NOT NULL,
		source VARCHAR(100) NOT NULL,
		title TEXT NOT NULL,
		content TEXT NOT NULL,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);`

	if _, err = db.Exec(createTableQuery); err != nil {
		log.Fatalf("Ошибка создания таблицы: %v", err)
	}

	fmt.Println("[Go] Успешное подключение к PostgreSQL")
	return db
}
