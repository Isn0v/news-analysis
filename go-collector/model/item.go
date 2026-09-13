package model

// NewsItem — единая схема данных, извлекаемых из RSS-лент.
type NewsItem struct {
	GUID         string
	URL          string   // нормализованный URL без UTM-параметров (ключ дедупликации)
	TimestampUTC string   // дата публикации (pubDate)
	UpdatedAtUTC string   // дата редактирования (atom:updated), если есть
	Source       string   // наш идентификатор источника ("beincrypto", "bitcoinist")
	OriginSource string   // оригинальный издатель (если есть тег <source>)
	OriginURL    string   // URL оригинального издателя
	Authors      []string // список всех авторов
	Title        string
	ImageURL     string
	Categories   []string // теги редакции
	Description  string   // краткий анонс
	Content      string   // полный текст статьи (content:encoded)
}

// Source — описание RSS-источника.
type Source struct {
	Name string
	URL  string
}
