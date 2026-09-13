package database

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/lib/pq"
)

// InitDB подключается к PostgreSQL по переменным окружения и применяет миграцию схемы.
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
		log.Fatalf("[DB] Ошибка подключения к базе: %v", err)
	}

	if err = db.Ping(); err != nil {
		log.Fatalf("[DB] База данных недоступна: %v", err)
	}

	if _, err = db.Exec(CreateTableQuery); err != nil {
		log.Fatalf("[DB] Ошибка создания таблицы: %v", err)
	}

	fmt.Println("[DB] Успешное подключение к PostgreSQL и проверка схемы")
	return db
}
