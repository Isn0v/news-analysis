# 🧠 `llm` (Financial Sentiment Analysis Service)

Микросервис квантитативного финансового NLP-анализа новостей криптовалютного рынка на базе современных LLM с гарантированным извлечением строго типизированных данных (Pydantic / OpenAI Structured Outputs).

---

## 🎯 Назначение

1. **Многомерная разметка сентимента:** формирование 11-мерного профиля влияния события на баланс спроса и предложения вместо примитивной 3-классовой классификации.
2. **Идентификация целевого горизонта:** определение времени реализации максимального ценового импакта (`target_horizon_hours`) и признака затухания/отката (`is_mean_reverting`).
3. **Фильтрация спекулятивного шума:** классификация новости на факт/катализатор или спекулятивный шум (`is_speculative` + `speculation_reason`).
4. **Гибридный инференс (Local + Cloud):** бесшовная работа как с локальной Ollama (DeepSeek-R1, Qwen2.5), так и с высокоскоростными облачными провайдерами (Groq Cloud с LPU-ускорением, Gemini, OpenAI) с автоматическим распознаванием токенов.
5. **Отказоустойчивый инференс:** двухконтурная обработка ответов моделей (включая модели с рассуждениями DeepSeek-R1) с автоматической очисткой тегов `<think>`, адаптивной обрезкой контекста и fallback-инжекцией JSON-схемы.

---

## 📁 Структура сервиса

```text
llm/
├── sql/
│   ├── fetch_unprocessed_batch.sql  # Атомарный захват пачки с SKIP LOCKED и установкой locked_until
│   ├── release_article_lock.sql     # Снятие блокировок со статей при прерывании или инфраструктурном сбое
│   ├── save_llm_result.sql          # Сохранение сентимента, сброс блокировки и processed=TRUE
│   └── get_table_stats.sql          # Подсчет статистики обработанных/ожидающих статей
├── tests/
│   ├── test_analyzer.py             # Тесты извлечения JSON, обрезки <think> и fallback
│   ├── test_db_integration.py       # Интеграционные тесты работы с PostgreSQL
│   ├── test_prompt.py               # Тесты сборки промпта аналитика
│   └── test_schema.py               # Тесты валидации схемы Pydantic
├── analyzer.py                      # LLM-клиент с обработкой <think> тегов, JSON fallback и Groq/OpenAI API
├── config.py                        # Pydantic Settings конфигурация сервиса (приоритет .env)
├── db.py                            # Асинхронный пул соединений PostgreSQL (psycopg3)
├── main.py                          # Точка входа с CLI-параметрами (--test-id, --token, --model)
├── prompt.py                        # Системный промпт финансового аналитика и fallback JSON-схема
├── queries.py                       # Загрузчик внешних .sql файлов
├── schema.py                        # Pydantic-модели и Enum'ы сентимента
├── worker.py                        # Демон пакетной обработки с asyncio.Semaphore
├── Dockerfile                       # Сборка на базе python:3.12-slim + uv
├── pyproject.toml / uv.lock         # Манифест зависимостей и лок-файл uv
└── README.md
```

---

## 📊 11-мерная квантитативная схема сентимента ([`schema.py`](file:///Users/isnov/Documents/Git/news-analysis/llm/schema.py))

Класс [`SentimentAnalysisResult`](file:///Users/isnov/Documents/Git/news-analysis/llm/schema.py#L58-L121) включает следующие параметры:

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `sentiment_score` | `float [-1.0 .. +1.0]` | Агрегированный вектор влияния на баланс спроса и предложения |
| `sentiment_label` | `enum` | Категория: `bullish`, `bearish`, `neutral` |
| `confidence` | `float [0.0 .. 1.0]` | Степень статистической уверенности модели в оценке |
| `impact_magnitude` | `int [1 .. 10]` | Сила рыночного шока: от 1 (локальный шум) до 10 (масштаб ETF/FTX) |
| `time_horizon` | `enum` | `immediate_1h_4h`, `short_term_1d_3d`, `medium_term_1w_1m`, `long_term_months` |
| `target_horizon_hours`| `int [1 .. 720]` | Расчетное количество часов до пикового эффекта цены |
| `is_mean_reverting` | `bool` | `True`, если ожидается быстрый откат/поглощение импульса |
| `is_speculative` | `bool` | `True` для спекулятивного шума/прогнозов, `False` для твердых фактов |
| `speculation_reason` | `str` | Обоснование классификации на спекуляцию или факт |
| `information_type` | `enum` | `hard_fact`, `rumor_leak`, `opinion_analysis`, `macro_release` |
| `market_surprise` | `enum` | `better_than_expected`, `worse_than_expected`, `in_line`, `not_applicable` |
| `transmission_channel`| `enum` | `liquidity_and_rates`, `fiat_debasement`, `geopolitical_risk`, `regulatory`, `defi_tech_exploit`, `general_crypto` |
| `affected_assets` | `list[AssetImpact]` | Список тикеров (`ticker`, `sentiment`, `reason`) |
| `detected_currencies`| `list[str]` | Список затронутых криптовалютных тикеров (напр. `['BTC', 'ETH']`) |
| `detected_categories`| `list[str]` | Стандартизированные категории рынка (Macro, Regulation, DeFi...) |
| `key_takeaways` | `list[str]` | 2–3 главных тезиса новости без «воды» |
| `reasoning` | `str` | Экономическое Chain-of-Thought обоснование механизма трансмиссии |

---

## ⚙️ Логика обработки и отказоустойчивость

### 1. Архитектура воркера ([`worker.py`](file:///Users/isnov/Documents/Git/news-analysis/llm/worker.py))
* **Распределенная очередь (`SKIP LOCKED`):** захват новостей выполняется через атомарный CTE (`SELECT ... FOR UPDATE SKIP LOCKED` + `UPDATE raw_news SET locked_until, locked_by`). Это позволяет запускать неограниченное количество параллельных воркеров на разных процессах, контейнерах или серверах без коллизий и дублирования работы.
* **Лизинг и таймаут блокировок:** если воркер аварийно завершится во время обработки статьи, блокировка автоматически истечет через `LOCK_TIMEOUT_MINUTES` (по умолчанию 15 минут), и статья вернется в очередь без вмешательства оператора.
* **Graceful Lock Release:** при инфраструктурных сбоях (падение соединения с LLM, Rate Limit) воркер мгновенно сбрасывает блокировку через `release_article_lock.sql`, чтобы другие живые инстансы могли подхватить задачу.
* **Контроль параллелизма:** параллельные запросы к LLM внутри одного инстанса ограничены семафором `asyncio.Semaphore(settings.max_concurrent_requests)`.
* **Защита от «ядовитых пилюль»:** в случае критической ошибки парсинга или несоответствия формата воркер не зависает, а вызывает `save_llm_error()` с записью ошибки в `llm_result` и выставляет `processed = TRUE`.

### 2. Двухконтурный инференс ([`analyzer.py`](file:///Users/isnov/Documents/Git/news-analysis/llm/analyzer.py))
* **Контур 1 (Structured Outputs API):** вызов `client.beta.chat.completions.parse()` со строгой схемой `response_format=SentimentAnalysisResult`. Мыслительный процесс `message.reasoning` переносится в поле `reasoning`.
* **Контур 2 (JSON Object & Regex Fallback):** если эндпоинт не поддерживает strict json_schema (например, Groq или ряд открытых моделей), сервис автоматически переключается на `response_format={"type": "json_object"}`. В системный промпт инжектируется полный шаблон всех 11 полей (`FALLBACK_JSON_INSTRUCTION`).
* **Очистка тегов `<think>`:** для моделей с открытым рассуждением (DeepSeek-R1) теги `<think>.*?</think>` удаляются, а валидный JSON извлекается регулярным выражением и валидируется через `SentimentAnalysisResult.model_validate_json()`.
* **Адаптивный контекст:** при ошибке превышения контекста токенов (`BadRequestError`) текст статьи автоматически усекается до 2000 символов для повторной попытки.

---

## ⚙️ Конфигурация ([`config.py`](file:///Users/isnov/Documents/Git/news-analysis/llm/config.py))

Конфигурация сервиса управляется через Pydantic Settings с поддержкой каскадной загрузки: `("../.env", ".env")`. Настройки из корневого файла `.env` проекта являются единым источником правды для Docker Compose, а локальный `llm/.env` позволяет локально переопределять параметры.

| Переменная | По умолчанию | Описание |
| :--- | :--- | :--- |
| `POSTGRES_HOST` | `localhost` | Хост базы данных PostgreSQL |
| `POSTGRES_PORT` | `5432` | Порт PostgreSQL |
| `POSTGRES_USER` | `trader` | Пользователь БД |
| `POSTGRES_PASSWORD` | *(Обязательно)* | Пароль БД |
| `POSTGRES_DB` | `crypto_news` | Имя базы данных |
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | URL OpenAI-совместимого эндпоинта инференса |
| `LLM_API_KEY` | `ollama` | API-ключ инференса |
| `GROQ_API_KEY` | `None` | Ключ Groq Cloud (`gsk_...`). При указании автоматически перенаправляет запросы на `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | `deepseek-r1:14b` | Название модели (напр. `deepseek-r1:14b`, `qwen/qwen3.8-27b`, `gpt-4o-mini`) |
| `LLM_TEMPERATURE` | `0.1` | Температура генерации |
| `LLM_NUM_CTX` | `16384` | Размер контекстного окна токенов (только для Ollama) |
| `LLM_TIMEOUT` | `120.0` | Таймаут HTTP-запроса (секунды) |
| `BATCH_SIZE` | `3` | Количество новостей за одну выборку |
| `MAX_CONCURRENT_REQUESTS`| `2` | Число одновременных запросов к LLM (Semaphore) |
| `MAX_CONTENT_CHARS` | `4000` | Максимальная длина статьи в промпте |
| `POLL_INTERVAL_SECONDS` | `10` | Пауза при пустой очереди |
| `WORKER_ID` | Auto-generated (`worker-{host}-{uuid}`) | Уникальный идентификатор инстанса воркера |
| `LOCK_TIMEOUT_MINUTES` | `15` | Таймаут удержания блокировки статьи в минутах |

> 💡 **Автоопределение Groq Cloud:** Если `GROQ_API_KEY` задан или `LLM_API_KEY` начинается с префикса `gsk_`, сервис автоматически подставит `LLM_BASE_URL=https://api.groq.com/openai/v1` и модель `qwen/qwen3.8-27b` (если модель не была задана явно), гарантируя ультрабыстрый инференс (~2.5 сек на статью) без нагрузки на локальный GPU.

---

## 🚀 Запуск и CLI-интерфейс ([`main.py`](file:///Users/isnov/Documents/Git/news-analysis/llm/main.py))

### 1. Локальный запуск демона через `uv`
```bash
cd llm
uv sync
uv run python main.py
```

Или из корня репозитория:
```bash
make llm-run
```

### 2. Масштабирование: запуск нескольких параллельных воркеров
Благодаря распределенному захвату очереди `SKIP LOCKED`, вы можете запустить произвольное число параллельных процессов:
```bash
# Воркер 1 (например, на локальном Apple MLX / GPU):
WORKER_ID=worker-mlx uv run python main.py

# Воркер 2 (параллельно на Groq Cloud API):
WORKER_ID=worker-groq GROQ_API_KEY=gsk_... uv run python main.py
```
Оба воркера будут параллельно разбирать одну и ту же очередь без коллизий.

### 3. Тестирование одиночной новости по ID (`--test-id`)
Позволяет быстро протестировать промпт и ответ модели на конкретной статье из БД без непрерывного опроса очереди:
```bash
# Тест с локальной Ollama:
uv run python main.py --test-id 18643

# Тест с облачным токеном Groq и выбранной моделью:
uv run python main.py --test-id 18643 --token gsk_your_key_here --model qwen/qwen3.8-27b
```

### 4. Переопределение параметров инференса через флаги CLI
```bash
uv run python main.py --token gsk_xxx --model qwen/qwen3.8-27b --base-url https://api.groq.com/openai/v1
```

### 5. Локальный инференс на Apple Silicon (MLX & Ollama)
```bash
# Вариант 1 (Рекомендуется для Apple Silicon — нативный Apple MLX сервер):
make mlx-serve
# Поднимает OpenAI-совместимый сервер на порту 8080 с моделью mlx-community/Qwen3.8-27B-4bit,
# 4-битным KV-кэшем и нативным reasoning_effort="low".

# Вариант 2 (Через локальную Ollama с оптимизированным контекстом и температурой):
make qwen-ollama-setup
# Собирает модель qwen-fast на базе models/Modelfile.qwen (num_ctx 8192, temp 0.2).
```

---

## 🧪 Запуск тестов

Тестовый набор покрывает Pydantic-схему, удаление тегов `<think>`, fallback парсинг поврежденного JSON, шаблонизацию промпта и интеграцию с базой данных:

```bash
# Из корня репозитория:
make test-llm

# Или напрямую в папке сервиса:
cd llm
uv run python -m pytest -v
```
