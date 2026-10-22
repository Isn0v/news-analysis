package database

import (
	"database/sql"

	"github.com/Isn0v/news/collector/model"
	"github.com/lib/pq"
)

// Repository инкапсулирует операции записи и чтения новостей в PostgreSQL.
type Repository struct {
	db *sql.DB
}

// NewRepository создаёт новый экземпляр репозитория.
func NewRepository(db *sql.DB) *Repository {
	return &Repository{db: db}
}

// Save сохраняет новость в базу данных.
// Возвращает (true, nil), если новость была сохранена,
// и (false, nil), если она была пропущена как дубликат по URL.
func (r *Repository) Save(item model.NewsItem) (bool, error) {
	market := item.Market
	if market == "" {
		market = "moex"
	}

	result, err := r.db.Exec(InsertNewsQuery,
		toNullString(item.GUID),
		item.URL,
		item.TimestampUTC,
		toNullString(item.UpdatedAtUTC),
		item.Source,
		toNullString(item.OriginSource),
		toNullString(item.OriginURL),
		pq.Array(item.Authors),
		item.Title,
		toNullString(item.ImageURL),
		pq.Array(item.Categories),
		item.Description,
		item.Content,
		market,
	)
	if err != nil {
		return false, err
	}

	rows, err := result.RowsAffected()
	if err != nil {
		return false, err
	}

	return rows > 0, nil
}

// toNullString превращает пустые строки в SQL NULL.
func toNullString(s string) sql.NullString {
	return sql.NullString{String: s, Valid: s != ""}
}
