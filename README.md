# 🚀 News Analysis & Crypto Sentiment Engine

Высокопроизводительный аналитический комплекс для автоматизированного сбора, дедупликации и глубокого финансового NLP-анализа криптовалютных новостей и макроэкономических релизов в реальном времени.

---

## 🏗 Архитектура системы

Комплекс построен по микросервисной архитектуре и состоит из трех ключевых компонентов, объединенных через Docker Compose:

```mermaid
flowchart TD
    subgraph Sources["16 RSS/Atom Источников (Tier 1-4)"]
        S1["Расследования (Protos, Unchained...)"]
        S2["Крупные СМИ (CoinDesk, BeInCrypto...)"]
        S3["Новости (NewsBTC, ZyCrypto...)"]
        S4["Авторские эссе (Arthur Hayes, Cobie...)"]
    end

    subgraph Collector["go-collector (Go 1.24)"]
        FanIn["Параллельный опрос (Fan-In Pattern)"]
        Clean["Очистка UTM, дедупликация URL, WAF Bypass"]
    end

    subgraph Storage["Хранилище (PostgreSQL 15)"]
        DB[("raw_news (JSONB + Индексы)")]
    end

    subgraph LLMService["llm-worker (Python 3.12 + uv)"]
        Worker["SentimentWorker (Async Queue Daemon)"]
        Parser["Pydantic Structured Parser + Fallback"]
    end

    subgraph Inference["LLM Инференс"]
        Ollama["Ollama (DeepSeek-R1:14b / Qwen2.5)"]
        CloudAPI["Облачные API (DeepSeek / OpenAI / Groq)"]
    end

    Sources --> FanIn --> Clean --> DB
    DB <-->|"SELECT (WHERE processed=FALSE) / UPDATE llm_result"| Worker
    Worker <--> Parser <--> Ollama & CloudAPI
```

1. **`go-collector` (Go 1.24):**
   * Конкурентный сборщик на горутинах (паттерн Fan-In).
   * Опрос 16 очищенных авторитетных источников с извлечением полного текста (`content:encoded`).
   * Нормализация URL (удаление UTM-меток, трекеров) и дедупликация на уровне БД (`ON CONFLICT (url) DO NOTHING`).
   * Обход WAF-защиты (Cloudflare, Sucuri) через эмуляцию Desktop User-Agent.

2. **`db` (PostgreSQL 15):**
   * Центральное хранилище сырых статей и результатов квантитативной разметки.
   * Партиционированный индекс `idx_raw_news_unprocessed` по `(timestamp_utc DESC) WHERE processed = FALSE` для мгновенной выборки новых статей воркером.
   * Поле `llm_result JSONB` для гибкого хранения структурированного отчета.

3. **`llm` (Python 3.12 + uv):**
   * Асинхронный воркер (`SentimentWorker`) с семафорным контролем параллелизма.
   * Гарантированная Pydantic-валидация через OpenAI-совместимый протокол Structured Outputs.
   * Поддержка цепочек рассуждений моделей DeepSeek-R1 (автоматическое извлечение и изоляция блоков `<think>...</think>`).
   * Внешние `.sql` файлы для работы с БД через пул соединений `psycopg3`.

4. **`market-evaluator` (Python 3.12 + uv):**
   * Микросервис квантитативного анализа рыночной реакции котировок (Event Study Engine).
   * Автоматическая выгрузка OHLCV-свечей с публичного API Binance вокруг времени публикации статьи ($t_0 - 4\text{ч} \dots t_0 + 24\text{ч}$).
   * Расчет доходностей (+15м, +1ч, +4ч, +24ч), пре-новостных утечек (Pre-event Drift), всплесков объемов и просадок.
   * Автоматическая валидация прогнозов LLM (Win Rate / Directional Alignment) с записью в таблицу `news_market_impact`.

---

## 📊 Научная схема анализа сентимента

В отличие от примитивной трехклассовой классификации (positive/negative/neutral), сервис формирует **11-мерный квантитативный профиль** каждой новости:

| Параметр | Тип | Описание |
| :--- | :--- | :--- |
| **`sentiment_score`** | `float [-1.0 .. +1.0]` | Числовой вектор влияния на баланс спроса и предложения. |
| **`sentiment_label`** | `enum` | Категория: `bullish`, `bearish`, `neutral`. |
| **`confidence`** | `float [0.0 .. 1.0]` | Степень статистической уверенности модели в оценке. |
| **`impact_magnitude`** | `int [1 .. 10]` | Сила рыночного шока: от 1 (локальный шум) до 10 (события масштаба ETF/FTX). |
| **`time_horizon`** | `enum` | Временной лаг: `immediate_1h_4h`, `short_term_1d_3d`, `medium_term_1w_1m`, `long_term_months`. |
| **`information_type`** | `enum` | Природа данных: `hard_fact`, `rumor_leak`, `opinion_analysis`, `macro_release`. |
| **`market_surprise`** | `enum` | Фактор неожиданности: `better_than_expected`, `worse_than_expected`, `in_line`, `not_applicable`. |
| **`transmission_channel`** | `enum` | Макро-канал: `liquidity_and_rates`, `fiat_debasement`, `geopolitical_risk`, `regulatory`, `defi_tech_exploit`, `general_crypto`. |
| **`affected_assets`** | `array` | Список затронутых тикеров (`BTC`, `ETH`, `SOL`...) с индивидуальным сентиментом и причиной. |
| **`key_takeaways`** | `array[str]` | 2–3 главных тезиса новости без «воды». |
| **`reasoning`** | `string` | Экономическое обоснование (Chain-of-Thought) механизма передачи импульса. |

---

## 🌐 Источники данных (16 каналов)

Все источники прошли верификацию на отсутствие спама, реферальных ссылок и доступность полных текстов статей:

* **Tier 1 (Глубокие расследования и аналитика):** `Protos`, `Unchained Crypto` (Laura Shin), `Bitcoin Magazine`, `Smart Liquidity`.
* **Tier 2 (Крупнейшие медиа-издания):** `BeInCrypto`, `CryptoSlate`, `The Daily Hodl`, `Blockonomi`, `Finbold`, `Coinspeaker`.
* **Tier 3 (Новостные порталы):** `Bitcoinist`, `NewsBTC`, `CoinJournal`, `ZyCrypto`, `BitcoinWorld`, `NullTX`.
* **Tier 4 (Авторские эссе лидеров мнений):** `Arthur Hayes (Substack)`, `Cobie (Substack)`.

---

## ⚡️ Быстрый старт

### Требования

* **Docker** и **Docker Compose**
* **Ollama** (для локального инференса на Mac/Linux) с загруженной моделью:

  ```bash
  ollama run deepseek-r1:14b
  ```

### 1. Клонирование и запуск всех сервисов в Docker

```bash
# Клонируйте репозиторий
git clone https://github.com/Isn0v/news-analysis.git
cd news-analysis

# Запустите весь комплекс (PostgreSQL + Go Collector + LLM Worker)
make up
```

---

## ⚙️ Конфигурация (`llm/.env` / `docker-compose.yaml`)

| Переменная | По умолчанию | Описание |
| :--- | :--- | :--- |
| `POSTGRES_HOST` | `db` (docker) / `localhost` (local) | Хост базы данных PostgreSQL |
| `POSTGRES_PORT` | `5432` | Порт PostgreSQL |
| `POSTGRES_USER` | `trader` | Пользователь БД |
| `POSTGRES_PASSWORD` | `strongpassword` | Пароль БД |
| `POSTGRES_DB` | `crypto_news` | Имя базы данных |
| `LLM_BASE_URL` | `http://host.docker.internal:11434/v1` | URL OpenAI-совместимого эндпоинта LLM |
| `LLM_API_KEY` | `ollama` | API-ключ (для Ollama любое значение, для OpenAI/DeepSeek — реальный ключ) |
| `LLM_MODEL` | `deepseek-r1:14b` | Название модели (`deepseek-r1:14b`, `qwen2.5:14b`, `deepseek-chat` и др.) |
| `LLM_TEMPERATURE` | `0.1` | Температура генерации (минимальная для строгой детерминированности) |
| `LLM_NUM_CTX` | `16384` | Размер контекстного окна токенов |
| `LLM_TIMEOUT` | `120.0` | Таймаут HTTP-запроса к модели в секундах |
| `BATCH_SIZE` | `3` | Количество новостей, забираемых из БД за один шаг |
| `MAX_CONCURRENT_REQUESTS` | `2` | Количество параллельных запросов к LLM (Semaphore) |
| `MAX_CONTENT_CHARS` | `6000` | Максимальная длина статьи, передаваемая в промпт |
| `POLL_INTERVAL_SECONDS` | `10` | Пауза опроса очереди при отсутствии новых статей |
| `LOG_LEVEL` | `INFO` | Уровень логирования (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 🛠 Полезные команды (Makefile & Docker)

```bash
make up          # Собрать и запустить все контейнеры в фоне
make down        # Полная остановка с очисткой томов (volumes)
make stop        # Остановка контейнеров с сохранением данных в базе
make vendor      # Обновление зависимостей в go-collector/vendor/
make llm-run     # Локальный запуск LLM-воркера через uv

# Просмотр логов в реальном времени
docker compose logs -f llm           # Логи воркера сентимента
docker compose logs -f go-collector  # Логи сборщика новостей
docker compose ps                    # Проверить статус контейнеров
```

---

## 🔍 Полезные SQL-запросы для аналитики

Все вспомогательные аналитические запросы собраны в папке [`sql/`](file:///Users/isnov/git/news-analysis/sql):

```bash
# Проверить количество обработанных и ожидающих новостей:
docker compose exec -T db psql -U trader -d crypto_news -f /dev/stdin < sql/total_count.sql

# Посмотреть последние 3 размеченные новости с полным JSON-сентиментом:
docker compose exec -T db psql -U trader -d crypto_news -c "
SELECT id, title, source, processed_at, jsonb_pretty(llm_result) 
FROM raw_news 
WHERE processed = TRUE 
ORDER BY processed_at DESC 
LIMIT 3;
"
```

---

## 💡 Особенности инференса на Apple Silicon vs Linux

В архитектуре проекта учтены фундаментальные особенности работы с локальными моделями:

* **На macOS (M-серия):** Docker работает внутри виртуальной машины Linux, куда закрытый графический стек **Apple Metal не пробрасывается**. Поэтому Ollama запускается **нативно на хосте**, отдавая всю мощь объединенной памяти GPU, а контейнеры Docker обращаются к ней через сетевой мост `host.docker.internal:11434`.
* **На Linux (с картами NVIDIA):** Ollama может быть без потерь скорости запущена в отдельном контейнере Docker через `nvidia-container-toolkit`.
