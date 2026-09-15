package database

import (
	"database/sql"
	"fmt"
	"log"

	"github.com/Isn0v/news/collector/config"
	_ "github.com/lib/pq"
)

// InitDB подключается к PostgreSQL по конфигурации и применяет миграцию схемы.
func InitDB(cfg *config.Config) *sql.DB {
	psqlInfo := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		cfg.PostgresHost, cfg.PostgresPort, cfg.PostgresUser, cfg.PostgresPassword, cfg.PostgresDB)

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

