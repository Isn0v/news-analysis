# 🧠 `llm` (Financial Sentiment Analysis Service)

Микросервис квантитативного финансового NLP-анализа новостей криптовалютного рынка на базе современных LLM с гарантированным извлечением строго типизированных данных (Pydantic / OpenAI Structured Outputs).

---

## 🎯 Назначение

1. **Многомерная разметка сентимента:** формирование 11-мерного профиля влияния события на баланс спроса и предложения вместо примитивной 3-классовой классификации.
2. **Идентификация целевого горизонта:** определение времени реализации максимального ценового импакта (`target_horizon_hours`) и признака затухания/отката (`is_mean_reverting`).
3. **Фильтрация спекулятивного шума:** классификация новости на факт/катализатор или спекулятивный шум (`is_speculative` + `speculation_reason`).
4. **Отказоустойчивый инференс:** двухконтурная обработка ответов моделей (включая модели с рассуждениями DeepSeek-R1) с автоматической очисткой тегов `<think>` и адаптивной обрезкой контекста.

---

## 📁 Структура сервиса

```text
llm/
├── sql/
│   ├── fetch_unprocessed_batch.sql  # Выборка пачки необработанных новостей (FIFO)
│   ├── save_llm_result.sql          # Сохранение сентимента и обновление processed=TRUE
│   └── get_table_stats.sql          # Подсчет статистики обработанных/ожидающих статей
├── tests/
│   ├── test_analyzer.py             # Тесты извлечения JSON, обрезки <think> и fallback
│   ├── test_db_integration.py       # Интеграционные тесты работы с PostgreSQL
│   ├── test_prompt.py               # Тесты сборки промпта аналитика
│   └── test_schema.py               # Тесты валидации схемы Pydantic
├── analyzer.py                      # LLM-клиент с обработкой <think> тегов и fallback
├── config.py                        # Pydantic Settings конфигурация сервиса
├── db.py                            # Асинхронный пул соединений PostgreSQL (psycopg3)
├── main.py                          # Точка входа с обработкой сигналов завершения
├── prompt.py                        # Системный промпт финансового аналитика и шаблонизатор
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
* **FIFO-очередь:** обработка новостей строго в хронологическом порядке (`ORDER BY timestamp_utc ASC`), что необходимо для корректного формирования истории свечей.
* **Контроль параллелизма:** параллельные запросы к LLM ограничены семафором `asyncio.Semaphore(settings.max_concurrent_requests)`.
* **Защита от «ядовитых пилюль»:** в случае критической ошибки парсинга статьи воркер не зависает, а вызывает `save_llm_error()` с записью ошибки в `llm_result` и выставляет `processed = TRUE`.

### 2. Двухконтурный инференс ([`analyzer.py`](file:///Users/isnov/Documents/Git/news-analysis/llm/analyzer.py))
* **Контур 1 (Structured Outputs API):** вызов `client.beta.chat.completions.parse()` со строгой схемой `response_format=SentimentAnalysisResult`. Мыслительный процесс `message.reasoning` переносится в поле `reasoning`.
* **Контур 2 (Regex Fallback):** для моделей вроде DeepSeek-R1 удаляются теги `<think>.*?</think>`, после чего валидный JSON извлекается регулярным выражением и парсится через `SentimentAnalysisResult.model_validate_json()`.
* **Адаптивный контекст:** при ошибке превышения контекста токенов (`BadRequestError`) текст статьи автоматически усекается до 2000 символов для повторной попытки.

---

## ⚙️ Конфигурация ([`config.py`](file:///Users/isnov/Documents/Git/news-analysis/llm/config.py))

| Переменная | По умолчанию | Описание |
| :--- | :--- | :--- |
| `POSTGRES_HOST` | `localhost` | Хост базы данных PostgreSQL |
| `POSTGRES_PORT` | `5432` | Порт PostgreSQL |
| `POSTGRES_USER` | `trader` | Пользователь БД |
| `POSTGRES_PASSWORD` | *(Обязательно)* | Пароль БД |
| `POSTGRES_DB` | `crypto_news` | Имя базы данных |
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | URL OpenAI-совместимого эндпоинта инференса |
| `LLM_API_KEY` | `ollama` | API-ключ |
| `LLM_MODEL` | `deepseek-r1:14b` | Название модели инференса |
| `LLM_TEMPERATURE` | `0.1` | Температура генерации |
| `LLM_NUM_CTX` | `16384` | Размер контекстного окна токенов |
| `LLM_TIMEOUT` | `120.0` | Таймаут HTTP-запроса (секунды) |
| `BATCH_SIZE` | `3` | Количество новостей за одну выборку |
| `MAX_CONCURRENT_REQUESTS`| `2` | Число одновременных запросов к LLM (Semaphore) |
| `MAX_CONTENT_CHARS` | `4000` | Максимальная длина статьи в промпте |
| `POLL_INTERVAL_SECONDS` | `10` | Пауза при пустой очереди |

---

## 🚀 Запуск и тестирование

### Локальный запуск через `uv`
```bash
cd llm
uv sync
uv run python main.py
```

Или из корня репозитория:
```bash
make llm-run
```

### Запуск тестов
```bash
make test-llm
# или
cd llm && uv run pytest -v
```
