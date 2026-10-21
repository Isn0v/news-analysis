# 📥 Sentix Collector (`sentix-collector`) — News Ingestion Microservice

Высокопроизводительный асинхронный сервис сбора, нормализации и дедупликации новостей **Sentix** из 16 RSS/Atom каналов на языке Go.

---

## 🎯 Назначение

1. **Параллельный опрос источников:** конкурентный сбор новостей через горутины по паттерну Fan-In.
2. **Извлечение полного текста:** получение `content:encoded` и тегов статьи, а не только коротких анонсов (`description`).
3. **Нормализация и дедупликация:** удаление трекинговых UTM-меток из URL и атомарная дедупликация на уровне PostgreSQL (`ON CONFLICT (url) DO NOTHING`).
4. **Обход WAF:** эмуляция реального браузерного User-Agent для преодоления Cloudflare и Sucuri.

---

## 📁 Структура сервиса

```text
go-collector/
├── config/
│   ├── config.go            # Загрузка настроек окружения и .env
│   └── config_test.go       # Юнит-тесты парсинга конфигурации
├── database/
│   ├── db-init.go           # Инициализация sql.DB и авто-миграция схемы
│   ├── insert_news.sql      # SQL-запрос вставки статьи с дедупликацией
│   ├── queries.go           # Встраивание SQL-файлов через //go:embed
│   ├── repository.go        # Слой данных Repository для работы с raw_news
│   ├── repository_test.go   # Интеграционные тесты репозитория
│   └── schema.sql           # DDL схемы таблицы raw_news и индексов
├── model/
│   └── item.go              # Структуры NewsItem и Source
├── parser/
│   ├── rss.go               # Парсинг RSS/Atom, чистка UTM, извлечение авторов
│   └── rss_test.go          # Тесты очистки UTM и извлечения метаданных
├── sources/
│   └── sources.go           # 16 активных проверенных источников (Tier 1-4)
├── vendor/                  # Зафиксированные вендор-зависимости Go
├── Dockerfile               # Двухэтапная сборка минимального Alpine-образа
├── go.mod / go.sum          # Манифесты зависимостей Go 1.24
└── main.go                  # Точка входа, оркестрация каналов и Graceful Shutdown
```

---

## 🌐 Источники данных (16 каналов)

Все источники в [`sources/sources.go`](file:///Users/isnov/Documents/Git/news-analysis/go-collector/sources/sources.go) проверены на отсутствие спама пресейлов и отдают полный текст:

* **Tier 1 (Ресерч и расследования):** `protos`, `unchained`, `bitcoin_magazine`, `smartliquidity`.
* **Tier 2 (Крупные отраслевые СМИ):** `beincrypto`, `cryptoslate`, `dailyhodl`, `blockonomi`, `finbold`, `coinspeaker`.
* **Tier 3 (Порталы новостей и теханализа):** `bitcoinist`, `newsbtc`, `coinjournal`, `zycrypto`, `bitcoinworld`, `nulltx`.
* **Tier 4 (Авторские Substack-эссе лидеров мнений):** `arthur_hayes`, `cobie`.

---

## ⚙️ Конфигурация ([`config/config.go`](file:///Users/isnov/Documents/Git/news-analysis/go-collector/config/config.go))

Сервис автоматически загружает переменные из `.env`, `../.env` или окружения:

| Переменная | По умолчанию | Описание |
| :--- | :--- | :--- |
| `POSTGRES_HOST` | `localhost` | Хост PostgreSQL (`db` внутри Docker) |
| `POSTGRES_PORT` | `5432` | Порт PostgreSQL |
| `POSTGRES_USER` | `trader` | Имя пользователя базы данных |
| `POSTGRES_PASSWORD` | *(Обязательно)* | Пароль к базе данных |
| `POSTGRES_DB` | `crypto_news` | Имя базы данных |
| `COLLECTOR_POLL_INTERVAL_SECONDS` | `300` (5 мин) | Периодичность запуска цикла сбора |

---

## 🚀 Запуск и тестирование

### Локальный запуск
```bash
cd go-collector
go run main.go
```

### Запуск тестов
```bash
# Из корня репозитория:
make test-collector

# Или напрямую в папке сервиса:
cd go-collector && go test -v ./...
```

### Обновление зависимостей
```bash
make vendor
# или
cd go-collector && go mod tidy && go mod vendor
```
